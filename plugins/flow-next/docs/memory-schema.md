# Memory System

Persistent learnings that survive context compaction. Opt-in, categorized — v0.33.0+. One entry per file, YAML frontmatter, two tracks (`bug` / `knowledge`).

> **On by default, and droppable.** flow-next runs fully without this. The tree itself is nearly free — entries are written as a side effect of work already happening and read by search, never loaded wholesale; the layer with a price is the **audit sweep**, a pass over every entry judged against the current codebase. Leave memory on; run the sweep deliberately with `/flow-next:audit` after a refactor invalidates prior art, rather than on a schedule. See [`running-lean.md`](running-lean.md).

## Directory tree

```
.flow/memory/
├── bug/
│   ├── build-errors/
│   ├── test-failures/
│   ├── runtime-errors/
│   ├── performance/
│   ├── security/
│   ├── integration/
│   ├── data/
│   └── ui/
├── knowledge/
│   ├── architecture-patterns/
│   ├── conventions/
│   ├── tooling-decisions/
│   ├── workflow/
│   ├── best-practices/
│   └── decisions/                          # v0.39.0+ — load-bearing architectural choices
└── declined/                               # declined-scope ledger — one file per concept, agent-written prose
```

## Frontmatter schema (bug track)

```yaml
---
title: SQLite locked under concurrent writes
date: 2026-04-24
track: bug
category: runtime-errors
module: storage/sqlite
tags: [sqlite, concurrency, locking]
problem_type: race
root_cause: missing WAL mode
resolution_type: config-fix
---
```

## Frontmatter schema (knowledge track)

```yaml
---
title: Prefer flowctl rp wrappers over the direct RepoPrompt CLI
date: 2026-04-24
track: knowledge
category: conventions
module: scripts/ralph
tags: [rp, ralph, review]
applies_when: writing Ralph loop scripts or review shims
---
```

## Frontmatter schema (decisions — knowledge track, v0.39.0+)

```yaml
---
title: Use nearest-ancestor walk for GLOSSARY.md resolution
date: 2026-04-30
track: knowledge
category: decisions
module: glossary
tags: [glossary, resolution, walk]
decision_status: accepted          # proposed | accepted | superseded
alternatives_considered: |
  - always-root: simpler, but loses subdir flexibility
  - explicit-path: makes resolution opaque to skills
superseded_by: null                 # set when decision_status = superseded
---
```

Decision body convention: 1–3 sentence floor describing trade-offs, irreversibility, and surprise factor. The three decision-specific fields (`decision_status`, `superseded_by`, `alternatives_considered`) are permitted on any knowledge entry but specifically intended for the `decisions/` subtree. Constants `MEMORY_DECISION_FIELDS` / `MEMORY_DECISION_STATUSES` (alongside `MEMORY_KNOWLEDGE_FIELDS` / `MEMORY_STATUS`).

## Declined scope — `.flow/memory/declined/`

A ledger of scope the project decided **not** to build. One file per concept: `.flow/memory/declined/<concept-slug>.md`. It sits outside the two tracks — no frontmatter schema, no `flowctl memory` subcommand, no status lifecycle, and no dependence on `memory.enabled`; `memory init` does not create it and the audit sweep does not walk it. Agents write these files directly, the same way they write any memory prose, creating the directory on the first refusal. A repo that never declined anything has no directory, and every read site treats that as "nothing declined" and moves on.

**The write filter is a policy refusal.** A file is created the first time a feature or scope is declined **as a matter of product judgment** — we could build this, and we are choosing not to. Plan's YAGNI rejections that are policy-level, an interview decline, and a spec closed as won't-do are the three moments that qualify.

**Anti-poisoning rule: never write a file for "declined because it already exists."** A request answered by pointing at the shipped feature is not a refusal, and recording it as one teaches every future planner that a capability the repo *has* is scope the repo *rejected*. Same for "declined because it's already planned", "declined because it belongs in another spec", and "declined because the request was a misunderstanding". The ledger holds product judgment, nothing else.

File shape:

```markdown
# Bulk export

**Decision:** Not building bulk export.

Single-item export covers the actual workflow; bulk export drags in job
queues, progress state, and partial-failure semantics for a case no user
has hit yet.

## Prior requests
- 2026-05-02 — asked during planning for fn-71 (CSV dump of all specs).
- 2026-07-19 — raised again in the fn-88 interview (nightly archive).
```

**The file is the recurrence state.** `## Prior requests` is a dated append-list, and nothing else tracks how often the concept comes back — three entries under one decision is the signal that the decision deserves a fresh look, and it is visible by reading the file. Appending a request never reopens the decision on its own; only the user does that.

## Enable + init

```bash
flowctl config set memory.enabled true
flowctl memory init   # creates directory tree
```

## Add

```bash
flowctl memory add \
  --track bug \
  --category runtime-errors \
  --title "SQLite locked under concurrent writes" \
  --module storage/sqlite \
  --tags "sqlite,concurrency" \
  --body-file /tmp/writeup.md

flowctl memory add \
  --track knowledge \
  --category conventions \
  --title "Prefer flowctl rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph"
```

`--type pitfall|convention|decision` (the old API) still works but emits a deprecation warning. Removed in 0.36.0.

**Overlap scoring** runs on every `add` and the JSON response always emits `matches` (with scores) as a retrieval signal. `memory add` **always creates** a new entry unless the caller passes explicit `--update <id>` (fn-113 — flowctl never auto-mutates on high overlap). Moderate overlap may set `related_to: [existing-id]` on the new entry. Callers (skills) read `matches` and either re-run with `--update <id>` or accept the create.

## Query

```bash
flowctl memory list                                # default: active only
flowctl memory list --track bug                    # filter by track
flowctl memory list --category runtime-errors      # filter by category
flowctl memory list --status hardened              # only graduated entries
flowctl memory list --status all                   # include stale + hardened entries

flowctl memory search "sqlite locked"              # default: --status active
flowctl memory search "sqlite locked" --status stale     # only stale entries
flowctl memory search "sqlite locked" --status hardened  # only hardened entries
flowctl memory search "sqlite locked" --status all       # active + stale + hardened
flowctl memory search "rp wrappers" \
  --module scripts/ralph \
  --tags "rp,ralph" \
  --limit 5

flowctl memory read bug/runtime-errors/sqlite-locked-2026-04-24   # full id
flowctl memory read sqlite-locked-2026-04-24                       # slug+date
flowctl memory read sqlite-locked                                  # slug only (latest date)
flowctl memory read legacy/pitfalls.md                             # legacy flat file
flowctl memory read legacy/pitfalls#3                              # legacy entry (1-based)
```

Search scoring is weighted: title 5×, tags 3×, body 1.5×, misc 1×. Legacy hits surface as synthetic entries with `track: "legacy"`. Default `--status active` excludes **both** stale and hardened entries (audit-flagged advice stops polluting `memory-scout` output; a hardened lesson now lives in a gate, so re-injecting it as context is waste); pass `--status stale`, `--status hardened`, or `--status all` to include them.

## Entry status

Every entry carries an implicit `status`. The field is optional in frontmatter — its absence means `active`, so a plain entry never writes it.

| Status | Meaning | Set by | Companion fields written | Companion fields cleared |
|--------|---------|--------|--------------------------|--------------------------|
| `active` (default) | The lesson is live and re-injected as context | `mark-fresh` (drops the `status` key entirely) | `last_audited`; `audit_notes` only with `--audited-by` | `stale_reason`, `stale_date`, `hardened_into`, `audit_notes` |
| `stale` | Audit flagged the advice as no longer accurate | `mark-stale` | `last_audited`, `audit_notes` (from `--reason`) | `hardened_into` |
| `hardened` (fn-122) | The lesson graduated into an enforced gate — lint rule, CI step, or instruction-file rule | `mark-hardened` | `hardened_into` (from `--gate-ref`), `last_audited`; `audit_notes` only with `--audited-by` | `stale_reason`, `stale_date` |

**Validation is enum-only.** `validate_memory_frontmatter` checks that `status` is one of `active | stale | hardened` and that unknown keys are rejected; it does **not** require any companion field for a given status. The column above describes what the `mark-*` handlers write and clear, which is the contract that matters in practice — a hand-edited entry carrying `status: stale` with no `stale_reason` still validates.

`stale_reason` / `stale_date` are legal optional fields that flowctl's own `mark-stale` does not currently populate (it records the reason in `audit_notes` instead); they exist for hand-written and older entries, and the handlers clear them on any transition out of `stale`.

`hardened` is **not** a weaker `stale`: the lesson is more alive than before, just relocated out of the context window and into something that fires on its own. The entry file stays on disk with its body intact so provenance survives — "why does this lint rule exist?" stays answerable.

Optional frontmatter fields that carry status: `status`, `stale_reason`, `stale_date`, `hardened_into`, `last_audited`, `audit_notes`.

`hardened_into` is stored **verbatim**; flowctl validates only that `--gate-ref` is non-empty at the CLI boundary. The skill-side convention is `<path>#<rule-id> -- <note>`, e.g. `pyproject.toml#DTZ -- ruff select entry, bans naive datetimes`. Parsing that convention is judgment and stays in `/flow-next:audit`, not in flowctl.

Every mutation (`mark-stale`, `mark-fresh`, `mark-hardened`) clears the **other** statuses' companion fields, not just its own — no field from the prior status survives a transition. `stale → hardened` and `hardened → stale` are both legal; `mark-fresh` returns any status to `active` and drops both families.

### Cross-version behavior (honest contract)

`validate_memory_frontmatter` runs **only inside `write_memory_entry`** (`flowctl.py`, the single call site). Reads never validate. So against an older flowctl that predates `hardened`:

- **Reads pass through silently.** The old binary parses a `hardened` entry without complaint, and because its default status filter excludes only `stale`, it will **surface** that entry in default `memory list` / `memory search` / `memory-scout` results — the opposite of the intended exclusion. The failure mode is misclassification, not rejection.
- **Writes are refused, loudly.** Any attempt by that older flowctl to rewrite the entry (`mark-stale`, `mark-fresh`, `memory add --update`) fails validation on the unknown `hardened` status value and the unknown `hardened_into` field. The write aborts with an error; nothing is silently corrupted on disk.

**Mitigation is lockstep upgrade, not a shim.** The repo already requires the two flowctl copies — `plugins/flow-next/scripts/flowctl.py` and `.flow/bin/flowctl.py` — to move together; keep them in sync and no version straddles the enum. No compatibility shim exists or is planned: an enum extension cannot retroactively teach an old reader anything, and a second signalling mechanism would be cost without benefit in a repo that already mandates lockstep copies.

## Audit lifecycle (v0.37.0+)

`/flow-next:audit [mode:autofix] [scope hint]` walks `.flow/memory/`, reviews each entry against the current codebase, and decides per entry whether to **Keep / Update / Consolidate / Replace / Delete / Harden**. Interactive mode (default) asks via the platform's blocking-question tool; autofix mode applies unambiguous actions and marks ambiguous entries as stale. The skill is agent-native — host agent reads the workflow markdown and executes it directly using its own Read/Grep/Glob tools (no Python audit engine, no codex/copilot subprocess dispatch). Legacy flat files are skipped with a warning.

**Audit extensions (v0.39.0+):** Phase 0.5 (new) reads every `GLOSSARY.md` on the ancestor chain and audits each term against the current code (any references intact? renamed? gone?). Phase 0.1 (extended) auto-walks `knowledge/decisions/` alongside other categories. **Replace outcomes for decision entries are supersede-not-delete** — the audit writes a new entry with `decision_status: accepted` and sets the old entry's `decision_status: superseded` + `superseded_by: <new-id>`, preserving the historical trail. Other categories keep the existing Replace semantics.

**Harden (fn-122):** the sixth outcome. When an entry is correct **and** recurring (re-taught across runs — measured from `## Update` heading count and entry-file commit count, since no read-side usage telemetry exists) **and** mechanizable, the audit proposes graduating it into an enforced gate: a lint rule, a CI step, or a rule in the substantive `CLAUDE.md` / `AGENTS.md`. The gate is **verified live** before the lesson is retired (resolved lint config, a job that actually runs, the instruction file agents really read); verification failure leaves the entry `active` and reports a failed graduation. Only on success is the entry demoted via `flowctl memory mark-hardened`, keeping the file on disk as a pointer at the gate. Harden never auto-applies in `mode:autofix` — candidates are reported under Recommended only, because gate surfaces are shared repo infrastructure. Precedence when an entry qualifies for several outcomes: **correctness (Replace / Delete) > Consolidate > Harden** — a wrong lesson is never graduated, and a `related_to` cluster is merged first, since the cluster (not each member) is the Harden unit.

**Un-graduation:** on later audit runs, each hardened entry gets a gate-liveness check against the surface named by `hardened_into`. Gate still present → the entry is reported as still-hardened and not re-investigated in full. Gate gone or inactive → the audit proposes `flowctl memory mark-fresh <id>`, which returns the entry to `active` and drops `hardened_into` so the lesson re-enters the context window. A gate upgrade (instruction-file rule promoted to a lint rule) is just another `mark-hardened` — idempotent, replaces `hardened_into`.

Three flowctl helpers back the audit lifecycle (also callable directly):

```bash
# Mark an entry stale (used by /flow-next:audit, also callable directly)
flowctl memory mark-stale <id> --reason "module renamed in PR #123"
flowctl memory mark-stale <id> --reason "..." --audited-by "/flow-next:audit"
flowctl memory mark-stale <id> --reason "..." --json

# Graduate a recurring lesson into a gate (fn-122) — demote the entry to a pointer
flowctl memory mark-hardened <id> \
  --gate-ref "pyproject.toml#DTZ -- ruff select entry, bans naive datetimes" \
  [--audited-by "/flow-next:audit"] [--json]

# Clear the stale flag OR un-graduate a hardened entry (both return it to active)
flowctl memory mark-fresh <id>
```

`mark-stale` sets `status: stale`, stamps `last_audited` (UTC date), records `audit_notes` from `--reason`, and drops any `hardened_into`. Body is never modified. Idempotent — re-marking replaces `audit_notes` and re-stamps the date.

`mark-hardened` sets `status: hardened` and `hardened_into` (from the required `--gate-ref`, stored verbatim), stamps `last_audited`, clears the stale-only fields, and records `audit_notes` when `--audited-by` is given. Body untouched; the file is never removed, on any track — including `knowledge/decisions/`, where supersession fields (`decision_status`, `superseded_by`, `alternatives_considered`) are preserved alongside the new status. Idempotent: re-marking replaces `hardened_into` (`last_audited` is date precision, so a same-day re-mark is unobservable on that field).

`mark-fresh` returns the entry to `active` — it drops `status`, `stale_reason`, `stale_date`, `hardened_into`, and `audit_notes`, then stamps `last_audited`. It is both the un-stale and the un-graduation escape hatch.

## Migrate legacy → categorized (v0.37.0+)

`/flow-next:memory-migrate [mode:autofix] [scope hint]` is the recommended path. Agent-native skill — host agent reads each legacy entry, classifies it into the right `(track, category)` pair using its own intelligence + repo context, writes a categorized entry via `flowctl memory add`. Interactive mode (default) asks via the platform's blocking-question tool on ambiguous entries; autofix mode accepts mechanical defaults and logs ambiguous as `needs-review`. Optional scope hint narrows to a single legacy file (e.g. `/flow-next:memory-migrate pitfalls.md`). Phase 4 cleanup writes a self-ignoring `.flow/memory/_migrated/.gitignore` and renames originals on user consent (autofix declines by default; never auto-deletes).

```bash
flowctl memory list-legacy            # text mode: filename + entry count + mechanical default per entry
flowctl memory list-legacy --json     # {files: [{filename, entry_count, entries: [...]}]}
```

`memory list-legacy` is the parsing helper the skill consumes; also useful for ad-hoc inspection. Each entry carries `mechanical_track` / `mechanical_category` derived from the source filename so the agent has a sane default to override only when content warrants.

### Automation / CI fallback

```bash
flowctl memory migrate --dry-run      # print plan (mechanical-only)
flowctl memory migrate --yes          # apply (mechanical-only)
```

`flowctl memory migrate` is **deterministic-only** since v0.37.0 — uses the mechanical filename → `(track, category)` heuristic. The `--no-llm` flag is accepted-but-noop (kept for back-compat with scripted callers). For accurate per-entry classification, run the `/flow-next:memory-migrate` skill instead.

`migrate` is idempotent — re-running after legacy files are archived prints `No legacy files to migrate.` JSON mode refuses writes without `--yes` as a safety guard.

> **Removed in v0.37.0:** `FLOW_MEMORY_CLASSIFIER_BACKEND`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT` env vars are no longer consumed (subprocess classifier dispatch removed). Setting them now triggers a one-time stderr warning. Suppress via `FLOW_NO_DEPRECATION=1`.

## Surface the store in AGENTS.md / CLAUDE.md

Point agents at `.flow/memory/` with a one-line note in `AGENTS.md` / `CLAUDE.md` (or both). `/flow-next:audit` and setup already handle discoverability via Edit; there is no dedicated `flowctl memory` patch command.

## When enabled

- **Planning**: category-aware `memory-scout` runs in parallel with other scouts, returns track/category-tagged hits and prioritizes module matches.
- **Work**: worker reads relevant entries during re-anchor.
- **Ralph**: worker writes structured bug-track entries via `memory add --track bug --category <c>` on NEEDS_WORK → SHIP. Overlap scoring emits `matches`; the worker re-runs with `--update <id>` when folding into a known prior entry.

Config lives in `.flow/config.json`, separate from Ralph's `scripts/ralph/config.env`.

## Review findings are evidence, memory is learning

Review receipts may carry the versioned structured `findings` container
documented in [`review-findings.md`](review-findings.md), and completion-review
receipts may additionally carry the per-criterion global-criteria compliance
array (`criteria: [{id, status, note?}]`, same doc § Global-criteria
compliance). That receipt stream is the authority for finding identity, round
lineage, snapshot binding, current status, and standing-criteria compliance. Memory has a different job: preserving a reusable explanation after a
non-trivial review fix.

After a `NEEDS_WORK` → `SHIP` transition, Work may synthesize a bug-track entry
from the review finding and the fix. The entry describes the problem, failed
approach, solution, and prevention. It does not copy the receipt's currentness
role:

- memory `status` (`active`, `stale`, `hardened`) describes whether the lesson
  should be re-injected, not whether a review finding is open or fixed;
- auditing or hardening memory never mutates a receipt;
- deleting, replacing, or consolidating memory never resolves a finding; and
- a stale receipt remains stale even when a related memory entry is active.

Consumers preserve both when available: receipt lineage for the review record,
memory for recurrence-prevention context. They must not infer resolution state
across the boundary.

## Upgrading from 0.32.x

1. `git pull && (reinstall plugin)`.
2. **Recommended:** run `/flow-next:memory-migrate` for agent-native per-entry classification (host agent reads each legacy entry and picks the right `(track, category)` with full repo context). Or `/flow-next:memory-migrate mode:autofix` to accept mechanical defaults without prompts.
3. **Automation alternative:** `flowctl memory migrate --dry-run` then `flowctl memory migrate --yes` for deterministic mechanical-only classification (legacy files move to `.flow/memory/_legacy/`; migration is idempotent).
4. Optional: add a one-line `.flow/memory/` pointer in `AGENTS.md` / `CLAUDE.md` so agents without flow-next skills still find the store.

Until migration runs, legacy flat files continue to work; `list` / `read` / `search` read both.

## See also

- [`architecture.md`](architecture.md) — `.flow/` directory layout including the `memory/` tree.
- [`review-findings.md`](review-findings.md) — structured receipt identity,
  currentness, bounds, fallback, and the consumer boundary with memory.
- [`glossary.md`](glossary.md) — pairs naturally with the `knowledge/decisions/` subtree (terminology + load-bearing choices).
- [`strategy.md`](strategy.md) — `/flow-next:capture` source-tags strategy-derived AC as `[strategy:<track>]`; decisions are recorded via memory when capture refuses to write against an active track.
- [`flowctl.md`](flowctl.md) — full `flowctl memory` reference (every subcommand, flag, JSON shape).
