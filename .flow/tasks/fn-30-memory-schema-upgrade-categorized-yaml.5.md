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
  --symptoms "<what went wrong>" \
  --root-cause "<what caused it>" \
  --body-file /tmp/memory-body.md
\`\`\`

Where `/tmp/memory-body.md` contains structured markdown with Problem / What Didn't Work / Solution / Prevention sections.

Optional flags the impl auto-fills with sensible defaults when omitted (fn-30.2):
- `--problem-type` — derived from `--category` (e.g. `runtime-errors` → `runtime-error`, `build-errors` → `build-error`, `test-failures` → `test-failure`; for other categories, defaults to `build-error`). Pass explicitly only when the category-derived default is wrong.
- `--resolution-type` — defaults to `fix`.
- `--symptoms` — defaults to the title when omitted.
- `--root-cause` — defaults to `(unspecified)` when omitted; prefer populating it for useful entries.

The overlap-detection in `memory add` handles duplicates automatically — if this pattern has been captured before, the existing entry is updated instead of a new one being created. No deduplication burden on the worker.

<!-- Updated by plan-sync: fn-30.2 auto-derives problem-type/resolution-type/symptoms defaults; --problem-type no longer required at the CLI. -->


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

1. Call `flowctl memory list --json` and/or `flowctl memory search <q> --json` (fn-30.3 already ships these) — no direct filesystem walking needed
2. Parse the returned entries + legacy descriptors for track/category context
3. Return results with track/category context

CLI shapes landed in fn-30.3 (use these — don't reinvent):

- `flowctl memory list --json` → `{entries: [{entry_id, title, track, category, module, tags, date, status, path}, ...], legacy: [{filename, path, entries, legacy_type}, ...], count, status}`
- `flowctl memory search <q> --json` → `{query, matches: [{entry_id, title, track, category, module, tags, score, snippet, path, legacy?}, ...], count}`
- Legacy hits in `search` appear with `track: "legacy"`, `category` set from the legacy-file map (`pitfall`/`convention`/`decision`), and an `entry_id` like `legacy/pitfalls#3`.
- `list` accepts `--track`, `--category`, `--status active|stale|all` (default active).
- `search` accepts `--track`, `--category`, `--module`, `--tags "a,b"`, `--limit N`.

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
- Filter by task context: if task touches `src/auth.ts`, prefer `flowctl memory search --module src/auth.ts` or post-filter on the `module` field; `flowctl memory list --category <c>` also works when the category is known
- Return compact summaries (title + one-sentence why-relevant), not full entry bodies

<!-- Updated by plan-sync: fn-30.3 ships `flowctl memory list/search --json` with concrete shapes `{entries, legacy, count, status}` and `{query, matches, count}`; scout should call those CLIs instead of walking the filesystem directly. -->


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
