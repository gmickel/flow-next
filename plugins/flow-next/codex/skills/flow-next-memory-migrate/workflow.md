# /flow-next:memory-migrate workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
MEMORY_DIR="$REPO_ROOT/.flow/memory"
MIGRATED_DIR="$MEMORY_DIR/_migrated"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. Mode + scope hint come from the SKILL.md mode-detection block (`MODE` = `interactive` | `autofix`, `SCOPE_HINT` = remainder, may be empty or a legacy filename like `pitfalls.md`).

If `.flow/memory/` does not exist, print `No .flow/memory/ directory — run \`$FLOWCTL memory init\` first.` and exit cleanly. Nothing to migrate.

If no legacy flat files exist (`pitfalls.md`, `conventions.md`, `decisions.md` all absent under `$MEMORY_DIR`), print `No legacy files to migrate.` and exit cleanly.

---

## Phase 0: Detect & enumerate

**Goal:** find every legacy flat file with parseable entries, skip already-migrated ones, narrow by scope hint, decide interaction path.

### 0.1 — Run `flowctl memory list-legacy --json`

```bash
"$FLOWCTL" memory list-legacy --json > /tmp/memory-migrate-legacy.json
```

Output shape (Task 2 ships this subcommand):

```json
{
  "files": [
    {
      "filename": "pitfalls.md",
      "path": ".flow/memory/pitfalls.md",
      "mechanical_track": "bug",
      "mechanical_category": "build-errors",
      "entries": [
        {
          "title": "OAuth callback drops state on retry",
          "body": "...",
          "tags": ["auth", "oauth"],
          "date": "2025-08-12"
        }
      ]
    }
  ]
}
```

Parse with `jq`:

```bash
LEGACY_COUNT=$(jq '.files | length' /tmp/memory-migrate-legacy.json)
TOTAL_ENTRIES=$(jq '[.files[].entries | length] | add // 0' /tmp/memory-migrate-legacy.json)
```

If `LEGACY_COUNT == 0` or `TOTAL_ENTRIES == 0`: print `No legacy files to migrate.` and exit cleanly.

### 0.2 — Idempotency check (skip already-migrated)

For each file in the list-legacy output, check whether a Phase 4 backup already exists:

```bash
ALREADY_MIGRATED=()
for filename in $(jq -r '.files[].filename' /tmp/memory-migrate-legacy.json); do
  if [[ -f "$MIGRATED_DIR/${filename}.bak" ]]; then
    ALREADY_MIGRATED+=("$filename")
  fi
done
```

Files in `ALREADY_MIGRATED` are filtered out of the migration set. They surface in the report as `Skipped (already migrated)` with their backup path.

This is the cheapest idempotency check — re-running migrate after a clean Phase 4 cleanup is a no-op for those files. The remaining files in the list-legacy output are the ones to migrate.

### 0.3 — Apply scope hint (when present)

If `SCOPE_HINT` is non-empty, narrow the candidate set. Match in this order — first match wins:

1. **Exact filename** — `pitfalls.md`, `conventions.md`, or `decisions.md`. Filter to that file only.
2. **Stem match** — `pitfalls` (no extension). Same as exact filename.
3. **Anything else** — print `Scope hint "<hint>" did not match a known legacy filename. Valid: pitfalls.md, conventions.md, decisions.md.` and abort.

When SCOPE_HINT is empty, all remaining (non-skipped) files are in scope.

### 0.4 — Triage summary

Compute working set after idempotency + scope filtering. Print to stderr:

```
Memory migration triage
=======================
Legacy files in scope: <N>
Already migrated (skipped): <K>
Total entries to classify: <M>
Mode: <interactive|autofix>
```

Per file in scope:

```
- pitfalls.md: 7 entries → default bug/build-errors
- conventions.md: 4 entries → default knowledge/conventions
```

### 0.5 — Confirmation gate (interactive only)

Interactive: ask via blocking-question tool before starting Phase 1:

```
Found <M> entries across <N> legacy files. Mechanical defaults will apply unless content
warrants otherwise. Proceed?

  1. Migrate all (recommended)
  2. Pick a single file
  3. Abort
```

If user picks "Pick a single file", ask which one (multiple choice from in-scope filenames) and narrow scope.

Autofix: skip the gate and proceed.

### Done when

- `WORKING_SET` (the in-memory list of `{filename, entries[], mechanical_track, mechanical_category}`) is finalized.
- `ALREADY_MIGRATED` list is captured for the eventual report.
- Confirmation passed (interactive) or skipped (autofix).

---

## Phase 1: Classify (one entry per tool call)

**Goal:** for each legacy entry, decide the final `(track, category)` pair using mechanical default + body-driven evidence.

### 1.1 — The "one entry per tool call" rule

Iterate entries one at a time. **Do not classify multiple entries in a single prompt or tool call.** Practice-scout flagged this as a real failure mode: agents under context pressure batch-classify in-prompt and silently skip entries. One-call-per-entry iteration discipline avoids this and gives clean per-entry verdict logging.

For each entry in `WORKING_SET`:

```python
# Pseudocode — actual loop is over the list-legacy JSON.
for file in working_set:
    for entry in file.entries:
        # one iteration = one entry = one decision
        classify_entry(entry, file.mechanical_track, file.mechanical_category)
```

### 1.2 — Per-entry classification steps

For each entry:

1. **Read** the entry's title, body, tags, source filename.
2. **Set the default** to `(file.mechanical_track, file.mechanical_category)` from the list-legacy output.
3. **Scan for override signals** in the title + body. See [phases.md](phases.md) §When to override for the catalog. Common overrides:
   - Title or body mentions race conditions, deadlocks, leaks, hangs → `bug/runtime-errors`
   - References to build/CI/compile failures → `bug/build-errors` (already the default for `pitfalls.md`)
   - Tooling decisions ("use pnpm not npm", "switch from Jest to Vitest") → `knowledge/tooling-decisions`
   - Architectural patterns ("we model X as a state machine", "every service registers via Y") → `knowledge/architecture-patterns`
   - Test-failure post-mortems → `bug/test-failures`
   - Performance fixes → `bug/performance`
   - Security incidents → `bug/security`
   - UI / a11y bugs → `bug/ui`
   - Data corruption / migration issues → `bug/data`
   - Integration / API contract issues → `bug/integration`
   - Workflow conventions ("PRs are squash-merged", "feature branches off main") → `knowledge/workflow`
4. **Decide:**
   - **Strong evidence for override** (the body unambiguously points at a different category) → use override; log `override` with one-line rationale.
   - **Weak / no signal** → take mechanical default; log `mechanical-default`.
   - **Ambiguous** (could plausibly be A or B; insufficient body context to pick) → see 1.3 below.
5. **Validate** the chosen `(track, category)` against the schema. The valid set is pinned in [phases.md](phases.md) §Valid track/category pairs. `flowctl memory add` validates again via `validate_memory_frontmatter`.

### 1.3 — Ambiguity handling

**Interactive mode:**

Use the platform's blocking-question tool (`AskUserQuestion` on Claude Code, `request_user_input` on Codex, `ask_user` on Gemini / Droid). Lead with the mechanical default as the recommendation:

```
Entry: "Auth token refresh race during logout" (from pitfalls.md)
Mechanical default: bug/build-errors
The body describes a runtime race condition, which suggests bug/runtime-errors.

Options:
  1. bug/runtime-errors (recommended override)
  2. bug/build-errors (mechanical default)
  3. Skip this entry — mark as needs-review
```

One question at a time. If `AskUserQuestion`'s schema isn't loaded on Claude Code, call `ToolSearch` with `select:AskUserQuestion` first.

**Autofix mode:**

Take the mechanical default. Log the entry as `needs-review` in the report so the user can re-classify post-migration via `/flow-next:audit` or manual intervention. Never silently override on autofix without strong evidence.

### 1.4 — Build per-entry classification record

For each entry, capture:

```yaml
source_file: pitfalls.md
title: "OAuth callback drops state on retry"
mechanical_default: [bug, build-errors]
final_classification: [bug, runtime-errors]
decision_kind: override   # or "mechanical-default" or "needs-review"
rationale: "Body describes async state-loss between callback retries — runtime concurrency, not build failure."
body: "..."
tags: ["auth", "oauth"]
date: "2025-08-12"
```

This record drives Phase 2 writes and the Phase 3 report.

### Done when

- Every entry in scope has a `final_classification` and a `decision_kind`.
- All overrides have a one-line rationale captured.
- Interactive mode has resolved every ambiguous entry via blocking question.
- Autofix mode has logged ambiguous entries as `needs-review`.

---

## Phase 2: Write categorized entries

**Goal:** persist each classified entry into the categorized tree via `flowctl memory add`.

### 2.1 — Per-entry write

For each classification record from Phase 1, write a tempfile holding the body, then invoke `flowctl memory add`:

```bash
TMPFILE=$(mktemp -t memory-migrate-body.XXXXXX.md)
# Write body to tempfile (preserve markdown verbatim — no transformation).
printf '%s\n' "$ENTRY_BODY" > "$TMPFILE"

"$FLOWCTL" memory add \
  --track "$TRACK" \
  --category "$CATEGORY" \
  --title "$TITLE" \
  --body-file "$TMPFILE" \
  --tags "$(printf '%s,' "${TAGS[@]}" | sed 's/,$//')" \
  --json
```

- **Tags**: forward tags from the legacy entry verbatim. Don't invent new ones.
- **Module**: legacy entries don't carry a `module` field — leave empty unless the body unambiguously names a single file path or module.
- **Date**: don't pass `--date`; let `flowctl memory add` use today's date for the new entry. The legacy entry's date is preserved in the migration report only (preserving history is what `git log` is for).

Capture the resulting entry id from the JSON output for the verification + report:

```bash
ENTRY_ID=$(jq -r '.id // empty' <<< "$ADD_OUTPUT")
```

If `flowctl memory add` exits non-zero, capture stderr and surface in the report under "Failed writes" — do not retry automatically (could be a real schema validation issue worth surfacing).

### 2.2 — Slug uniqueness

`flowctl memory add` already handles slug collisions by suffixing `-2`, `-3`, etc. — no special handling needed. Two entries titled "API rate limiting" land as `bug/integration/api-rate-limiting-2026-04-25.md` and `bug/integration/api-rate-limiting-2026-04-25-2.md`.

### 2.3 — Override detection (`flowctl memory add` overlap-detection)

`flowctl memory add` runs overlap detection against existing entries. High overlap updates the existing entry in place (returns the existing id); moderate overlap creates a new entry with `related_to: [<existing-id>]`. This is desired behavior — don't suppress it. Surface the outcome in the report so the user knows when migration merged an entry rather than creating a fresh one.

### 2.4 — Cleanup tempfile

```bash
rm -f "$TMPFILE"
```

### Done when

- Every classification record from Phase 1 has been written via `flowctl memory add`.
- Failed writes are captured (entry id will be empty for those).
- Tempfiles cleaned up.

---

## Phase 3: Verify + Report

**Goal:** confirm round-trip on every newly created entry, then print the migration report.

### 3.1 — Verify each new entry round-trips

For each non-empty `ENTRY_ID` from Phase 2, re-read via flowctl:

```bash
"$FLOWCTL" memory read "$ENTRY_ID" --json > /dev/null
```

If the read fails (non-zero exit), flag the entry as `verification-failed` in the report. Indicates a write or filesystem issue — the user should investigate before Phase 4 cleanup.

### 3.2 — Report structure

Print to stdout as markdown:

```text
Memory Migration Summary
========================
Legacy files processed: <N>   (skipped: <K> already migrated)
Entries migrated: <M>
Overrides (mechanical → agent-decided): <P>
Needs review (ambiguous, took mechanical default): <Q>
Verification failures: <V>
Failed writes: <F>
```

Then per-file detail:

```
- pitfalls.md (7 entries → 7 migrated)
  Mechanical default: bug/build-errors
  Overrides: 2
    - "Auth token refresh race during logout" → bug/runtime-errors
      (Body describes async state-loss between callback retries)
    - "Build slow after monorepo restructure" → bug/performance
      (Body recounts build-time perf regression, not a build failure)
  Needs review: 1
    - "Generic logging guidance" — body too abstract to pick build-errors vs best-practices
```

For each migrated entry, the per-entry id is available in the JSON dump but doesn't need to be enumerated unless the user asked for verbose output.

### 3.3 — Autofix two-section split

In autofix mode, split actions into:

- **Applied** — writes that succeeded.
- **Recommended** — actions that could not be written (e.g. permission denied, schema validation failed). Same detail as Applied; framed for a human to apply manually.

If all writes succeed, Recommended is empty. Phase 4 cleanup recommendations always land in Recommended on autofix.

### 3.4 — Confirmation gate before Phase 4 (interactive only)

After printing the report, ask:

```
Migration complete. <M> entries written.

Phase 4 — optional cleanup. The original flat files are still in place. Options:

  1. Rename originals to .flow/memory/_migrated/<filename>.bak (recommended)
     Self-ignoring directory: a `.gitignore: *` is added on first cleanup.
  2. Leave originals in place
  3. Show me the new entries first (re-print summary then ask again)
```

Autofix: skip the gate; default-decline cleanup; surface as a recommendation in the report.

### Done when

- Every newly created entry has been verified via `flowctl memory read`.
- Full report printed to stdout.
- Cleanup gate resolved (interactive) or skipped (autofix).

---

## Phase 4: Optional cleanup

**Goal:** rename originals to `.flow/memory/_migrated/<filename>.bak` for traceability. Self-ignoring directory pattern. NEVER auto-delete.

### 4.1 — When to run

- **Interactive mode + user picked option 1** in the Phase 3 cleanup gate.
- **Autofix mode** — never. Surface as recommendation in the Phase 3 report instead. Originals stay in place.

### 4.2 — Create `_migrated/` directory + self-ignoring gitignore

```bash
mkdir -p "$MIGRATED_DIR"

# Self-ignoring directory pattern: write `.gitignore: *` on first cleanup.
# This is the standard pattern (used by node_modules tooling, __pycache__, etc.).
# Avoids requiring the user to update the top-level .gitignore.
GITIGNORE_PATH="$MIGRATED_DIR/.gitignore"
if [[ ! -f "$GITIGNORE_PATH" ]]; then
  printf '*\n' > "$GITIGNORE_PATH"
fi
```

The `.gitignore` content is just `*` — every file in `_migrated/` is ignored by git, including the `.gitignore` itself. Standard self-ignoring pattern.

### 4.3 — Rename each migrated original

For each filename whose entries were migrated in this run (not already in `ALREADY_MIGRATED`):

```bash
mv "$MEMORY_DIR/$filename" "$MIGRATED_DIR/${filename}.bak"
```

Use `mv`, not `cp + rm`. Preserves filesystem inode for any reflinks.

### 4.4 — What NOT to do

- **Do not `git rm`** the originals. Rename only — leaves them on disk for the user to inspect.
- **Do not delete `_migrated/`** on subsequent runs. The presence of `<filename>.bak` is what Phase 0's idempotency check uses to skip already-migrated files.
- **Do not commit** the rename automatically. The skill itself doesn't commit — the user runs `git status` post-migration and decides. The `.gitignore: *` ensures the renamed `.bak` files won't accidentally get committed.

### 4.5 — Report cleanup outcome

Append to the Phase 3 report:

```
Cleanup
-------
Renamed: <list of originals → _migrated/.../*.bak>
Created: .flow/memory/_migrated/.gitignore (self-ignoring; first run only)
```

### Done when

- All migrated originals renamed (interactive + user consented).
- `_migrated/.gitignore` exists with content `*` if any rename happened.
- Cleanup outcome logged in the report.

---

## Manual smoke (acceptance R1, R3, R4, R5, R10, R11)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:memory-migrate` in a real session. Expected behavior:

- Phase 0 detects legacy files via `flowctl memory list-legacy --json`, skips already-migrated ones, applies scope hint, prints triage summary.
- Phase 1 iterates entries one per tool call; mechanical defaults applied unless body warrants override; ambiguous entries asked (interactive) or marked needs-review (autofix).
- Phase 2 writes via `flowctl memory add --track <t> --category <c> ...`. Slug uniqueness handled.
- Phase 3 verifies round-trip + prints report.
- Phase 4 (optional) renames originals to `_migrated/<filename>.bak`; first-run writes `_migrated/.gitignore: *`.

In autofix mode (`/flow-next:memory-migrate mode:autofix`), Phase 1 ambiguity routes to needs-review, Phase 4 default-declines, and the report is the sole deliverable.

If Phase 0 produces an empty `WORKING_SET` (all files already migrated, or no legacy files exist), the skill exits cleanly with the appropriate message.
