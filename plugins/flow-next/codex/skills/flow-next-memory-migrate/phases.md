# Memory migration — `(track, category)` decision tree

For each legacy entry, classify it into exactly one `(track, category)` pair. Calibration below mirrors the deterministic baseline in `flowctl.py` (`_memory_classify_mechanical` at line 6390 + `_DEPRECATED_TYPE_MAP` at line 4918) plus narrative guidance for when the entry's body warrants overriding the mechanical default. For the workflow phases that drive these decisions, see [workflow.md](workflow.md).

---

## Mechanical baseline (the default — applied when no body signal)

| Legacy filename | Default `(track, category)` |
|-----------------|-----------------------------|
| `pitfalls.md` | `bug/build-errors` |
| `conventions.md`| `knowledge/conventions` |
| `decisions.md` | `knowledge/tooling-decisions` |

This is what `flowctl memory list-legacy --json` emits as `mechanical_track` + `mechanical_category` per file. Take this default unless the entry's title + body unambiguously points at a different category.

---

## Valid track / category pairs (the schema)

The skill must only write entries with these pairs. `flowctl memory add` validates again, but pinning the valid set in the prompt avoids round-trips on rejected writes.

**Track `bug` categories:**

- `build-errors` — compile / lint / type-check / dependency-resolution failures
- `test-failures` — flaky tests, assertion mismatches, fixture issues, CI test failures
- `runtime-errors` — null dereferences, race conditions, leaks, hangs, exceptions in production code paths
- `performance` — slow queries, N+1, memory leaks, latency regressions
- `security` — auth bypass, injection, secret leakage, CSRF / XSS
- `integration` — API contract drift, schema mismatch, third-party service mishaps, wire-format issues
- `data` — corruption, partial writes, migration errors, encoding bugs
- `ui` — layout breakage, wrong colors, a11y regressions

**Track `knowledge` categories:**

- `architecture-patterns` — system design choices, structural patterns ("we model X as a state machine")
- `conventions` — naming, file layout, code style ("PascalCase for components, kebab-case for files")
- `tooling-decisions` — tool choice rationale ("use pnpm not npm because <reason>")
- `workflow` — process / branching / review patterns ("PRs are squash-merged", "feature branches off main")
- `best-practices` — generic guidance not specific to a tool or pattern ("always validate inputs at boundaries")

---

## When to override the mechanical default

The mechanical default is right ~70% of the time on real corpora. Override only when the entry's title + body provides high-confidence evidence for a different category.

### Override examples (from `pitfalls.md` mechanical default `bug/build-errors`)

| Body signal | Override to |
|-------------|-------------|
| "Race condition between callback handlers" | `bug/runtime-errors` |
| "Deadlock in worker pool when N workers > M tasks" | `bug/runtime-errors` |
| "Memory leak — promises never resolved" | `bug/runtime-errors` |
| "Test flakes when run in parallel mode" | `bug/test-failures` |
| "Assertion fails when running on CI but not locally" | `bug/test-failures` |
| "API call took 30s after migration to v2" | `bug/performance` |
| "Query runs N+1 in production" | `bug/performance` |
| "Token refresh leaked client secret" | `bug/security` |
| "CSRF cookie not set on logout" | `bug/security` |
| "Stripe webhook signature mismatch" | `bug/integration` |
| "GraphQL schema drift broke client" | `bug/integration` |
| "Migration partially applied — half the rows have new column" | `bug/data` |
| "User uploads UTF-16 names; we expected UTF-8" | `bug/data` |
| "Modal traps focus when escape pressed twice" | `bug/ui` |
| "Color contrast fails WCAG AA on dark theme" | `bug/ui` |

### Override examples (from `conventions.md` mechanical default `knowledge/conventions`)

| Body signal | Override to |
|-------------|-------------|
| "We model long-running jobs as a finite state machine" | `knowledge/architecture-patterns` |
| "Every service registers via the bus on startup" | `knowledge/architecture-patterns` |
| "Use pnpm not npm — workspace hoisting matters here" | `knowledge/tooling-decisions` |
| "Switched from Jest to Vitest for ESM compat" | `knowledge/tooling-decisions` |
| "PRs are squash-merged after one approval" | `knowledge/workflow` |
| "Feature branches off main; never off other features" | `knowledge/workflow` |
| "Always validate inputs at boundaries; trust the core" | `knowledge/best-practices` |

### Override examples (from `decisions.md` mechanical default `knowledge/tooling-decisions`)

| Body signal | Override to |
|-------------|-------------|
| "Decided to model orders as event-sourced aggregates" | `knowledge/architecture-patterns` |
| "Decided that PR titles follow Conventional Commits" | `knowledge/workflow` |
| "Decided we always run lint before push" | `knowledge/workflow` |
| "Decided naming convention: PascalCase components, kebab-case files" | `knowledge/conventions` |

### When in doubt

Take the mechanical default. The post-migration report flags it as `needs-review` (autofix) or asks the user (interactive). Re-classification later via `/flow-next:audit` Replace flow is cheap; a wrong override at migration time is silently misleading.

---

## Idempotency rules

### Pre-migration (Phase 0)

Before classifying anything from a legacy file, check whether it's already been migrated:

```bash
if [[ -f "$MEMORY_DIR/_migrated/${filename}.bak" ]]; then
 # Skip this file — Phase 4 already renamed it on a prior run.
 # Surface in report as "Skipped (already migrated): <filename>"
fi
```

The presence of `_migrated/<filename>.bak` is the canonical signal. Cheaper than diffing legacy entries against the categorized tree.

### Mid-migration (Phase 2)

`flowctl memory add` runs overlap detection. If a categorized entry with high overlap already exists (e.g. someone manually migrated one entry already, then re-ran the skill), the helper updates the existing entry in place rather than creating a duplicate. This is desired — the skill doesn't override that behavior.

### Post-migration (Phase 4)

After a successful run, Phase 4 renames originals:

```bash
mv "$MEMORY_DIR/$filename" "$MEMORY_DIR/_migrated/${filename}.bak"
```

Self-ignoring directory: on first cleanup, write `.flow/memory/_migrated/.gitignore` containing `*`. Standard pattern (used by `node_modules`, `__pycache__` tooling). Every file under `_migrated/` is gitignored, including the `.gitignore` itself. No top-level `.gitignore` change required.

### Re-running the skill

Re-running `/flow-next:memory-migrate` after a clean Phase 4:

- Phase 0 detects `_migrated/<filename>.bak`, skips that file, reports it as "Skipped (already migrated)".
- Net result: no-op for already-migrated files. Only newly-introduced legacy files (rare — would require someone re-creating `pitfalls.md` post-migration) get processed.

Re-running after Phase 4 was declined (originals still in place):

- Phase 0 sees no backups → all files in scope.
- `flowctl memory add` overlap detection prevents duplicate categorized entries even if the previous run already wrote them.
- Net result: idempotent at the categorized-tree level (no duplicates). The skill doesn't track per-entry "already migrated" state — it relies on `flowctl memory add`'s overlap detection.

---

## Decision tree (quick reference)

```
For each legacy entry:

 Read title + body + tags + source filename.

 Set default = (mechanical_track, mechanical_category) # from list-legacy

 Scan body for override signals (catalog above):
 - Strong evidence for a different category?
 yes → override + log rationale
 no → continue

 Validate (track, category) against schema:
 - In MEMORY_CATEGORIES[track]?
 yes → ready to write
 no → fall back to mechanical default + log as needs-review

 Ambiguous (could plausibly be A or B)?
 interactive → ask via blocking-question tool
 autofix → take mechanical default + log as needs-review

 Phase 2: flowctl memory add --track <t> --category <c> --title "..." --body-file <tmp>
```

---

## Rationale for the mechanical-default-first stance

The temptation in an LLM-driven migration is to "use AI to classify each entry intelligently" — but most legacy entries are pre-fn-30 ad-hoc memos, often without strong category signal. The mechanical default works:

- `pitfalls.md` was originally a build-failure / gotcha bucket → `bug/build-errors` is the median fit.
- `conventions.md` was a coding-style bucket → `knowledge/conventions` is the median fit.
- `decisions.md` was an architecture / tool-choice bucket → `knowledge/tooling-decisions` is the median fit.

The agent's intelligence is best spent on the 20-30% of entries that genuinely don't fit the median (the override examples above). Aggressive over-classification produces inconsistent results across runs and obscures the mechanical baseline that `_memory_classify_mechanical` already gets right cheaply.

The `needs-review` flag is the escape hatch: better to migrate everything with a sane default and surface uncertainty in the report than to block on ambiguous decisions or invent classifications without evidence.
