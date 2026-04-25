# /flow-next:audit workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
MEMORY_DIR="$REPO_ROOT/.flow/memory"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. Mode + scope hint come from the SKILL.md mode-detection block (`MODE` = `interactive` | `autofix`, `SCOPE_HINT` = remainder).

If `.flow/memory/` does not exist, print `No .flow/memory/ directory — run \`$FLOWCTL memory init\` first.` and exit cleanly. Nothing to audit.

---

## Phase 0: Discover & Triage

**Goal:** find every categorized memory entry, group by module / category, skip legacy + `_*` directories with a counted warning, then pick the lightest interaction path.

### 0.1 — Walk the categorized tree

Use Glob (not shell `find`) to avoid permission prompts on platforms where shell file ops gate behind permissions:

```
glob: .flow/memory/bug/**/*.md
glob: .flow/memory/knowledge/**/*.md
```

Filter results:

- **Skip** any path under `.flow/memory/_*` (e.g. `_audit/`, `_review/`).
- **Skip** entries whose direct parent is `.flow/memory/` itself (those are legacy flat files, handled in §0.2).
- **Keep** anything matching `.flow/memory/{bug,knowledge}/<category>/<slug>-<YYYY-MM-DD>.md`.

For each kept path, read the frontmatter (parser pattern from `prospect/workflow.md` §0.2 — stdlib Python is fine; PyYAML when available is nicer). Capture: `entry_id` (from path), `track`, `category`, `slug`, `date`, `title`, `module`, `tags`, `status`, plus the body for later investigation.

If the entry's `status` is `stale` already, surface it in the report under "Already stale" and skip investigation in autofix mode (mark-stale is idempotent — re-marking adds noise). In interactive mode, offer to refresh-investigate (rare path; user-driven).

### 0.2 — Detect legacy flat files

```bash
LEGACY_FILES=()
for legacy in pitfalls.md conventions.md decisions.md; do
  if [[ -f "$MEMORY_DIR/$legacy" ]]; then
    LEGACY_FILES+=("$legacy")
  fi
done
LEGACY_COUNT=$(( ${#LEGACY_FILES[@]} ))
```

If `LEGACY_COUNT > 0`, count entries inside (each legacy file is `---`-delimited segments — `flowctl memory list --json` surfaces them under a top-level `legacy` array):

```bash
LEGACY_ENTRY_COUNT=$("$FLOWCTL" memory list --json 2>/dev/null \
  | jq '[.legacy[]?.entries] | add // 0' 2>/dev/null || echo 0)
```

**Skip them.** Auditing legacy entries is half-broken: no frontmatter to write `status: stale` to, no track / category for scoping, references too dense to verify mechanically. The report will print:

```
Skipped legacy: <LEGACY_ENTRY_COUNT> entries across <files>.
Run `/flow-next:memory-migrate` first to make these auditable (or `flowctl memory migrate --yes` for deterministic mechanical-only conversion).
```

`<files>` is the comma-joined list (`pitfalls.md, conventions.md`). Continue with categorized entries only.

### 0.3 — Apply scope hint (when present)

When `SCOPE_HINT` is non-empty, narrow the candidate set in this order — first match wins:

1. **Track match** — `bug` or `knowledge` as a literal token. Filter to that track.
2. **Category match** — exact match against `MEMORY_CATEGORIES` enum (e.g. `runtime-errors`, `architecture-patterns`, `tooling-decisions`). Filter to that category across both tracks.
3. **Module match** — substring match against `frontmatter.module`. Useful when the user types `auth` or `plugins/flow-next/scripts/flowctl.py`.
4. **Tag match** — exact match against any value in `frontmatter.tags`.
5. **Title / body keyword** — case-insensitive substring search across `title` and `body`. Last resort because it can be noisy.

Print the strategy used and the count: `Scope hint "auth" matched module field on 4 entries.`

If no entries match, **interactive**: ask whether to (a) widen to all entries, (b) re-enter a different hint, (c) abort. **Autofix**: print `Scope hint "<hint>" matched zero entries — nothing to audit.` and exit cleanly.

### 0.4 — Count + route

Count remaining entries (`TOTAL`). Route:

| TOTAL | Path | Notes |
|-------|------|-------|
| 0 | exit cleanly | Print `No categorized memory entries found.` plus legacy skip note if any |
| 1-2 | **Focused** | Investigate directly, then present recommendation(s) |
| 3-8 | **Batch** | Investigate (parallel subagents on 3+), then present grouped recommendations |
| 9+ | **Broad** | Triage first: pick highest-impact cluster, recommend starting there (interactive) or process all clusters in impact order (autofix) |

### 0.5 — Broad-scope triage (only when `TOTAL >= 9`)

Group entries by `(module, category)` pair. For each cluster:

- Count entries.
- Note cross-references (`related_to` frontmatter field pointing into the same cluster).
- Spot-check drift: does the most-referenced file in the cluster still exist? Use Glob.

Compute impact: `cluster_score = entries + 2 * cross_refs + (3 if missing_anchor_file else 0)`. The highest-scoring cluster is the recommended starting area.

**Interactive:** present top cluster + 2 alternatives via blocking question:

```
Found 24 entries across 6 clusters.

The auth/runtime-errors cluster has 5 entries cross-referencing each other —
3 reference files that no longer exist on disk. Highest staleness signal.

Options:
  1. Start with auth/runtime-errors (recommended)
  2. Pick a different cluster
  3. Audit everything (will take longer)
```

**Autofix:** process all clusters in impact order (highest first). Print the queue order so the report shows what got prioritized.

### Done when

- `ENTRIES` (the in-memory list) is finalized for this run.
- Legacy skip count is captured for the eventual report.
- `MODE` × `TOTAL` × `SCOPE` resolution is clear (route picked).

---

## Phase 1: Investigate (per entry)

**Goal:** for each entry in scope, verify its claims against the current codebase and form a recommendation with evidence.

A memory entry has dimensions that can independently go stale:

- **References** — do the file paths, modules, and symbols mentioned in the body or `module` field still exist? If renamed, where did they move?
- **Solution** — does the recommended fix still match how the code actually works today? A file rename with a completely different implementation pattern is not just a path update.
- **Code examples** — if the body includes code snippets, do they reflect current implementation?
- **Related entries** — `related_to: [<id>, ...]` cross-references — do those entries still exist? Are they consistent?
- **Problem domain** — does the application still face the problem this entry solves? A bug entry about a deleted feature is misleading.

### 1.1 — Per-entry investigation steps

For each entry:

1. **Read** the file (already loaded in Phase 0; re-read body if it was elided).
2. **Verify the `module` field** — Glob for the path. If missing, Glob for the basename across the repo (renamed?). Grep for any class / function names mentioned in the body.
3. **Verify referenced files** in the body — same pattern. List broken references.
4. **Check git log** in the affected area (if the path resolves): `git log --oneline -10 -- <path>`. Recent activity = code is alive; long quiet = candidate for deletion if also unreferenced elsewhere.
5. **Search for successor patterns** — if the entry is a bug, Grep for the symptom keywords in the current codebase. If matches turn up in code that looks like a re-implementation, the problem domain may persist under a new shape (Replace, not Delete).
6. **Form a recommendation:** Keep / Update / Consolidate / Replace / Delete + 2-4 evidence bullets + confidence (low / medium / high).

Match investigation depth to entry specificity. An entry referencing exact file paths and code snippets needs more verification than one describing a general principle.

### 1.2 — Subagent dispatch (3+ independent entries)

When `TOTAL >= 3` AND the entries don't share heavy overlap (different modules / categories), dispatch parallel investigation subagents. Pick the primitive that exists in your harness:

| Platform | Primitive | Subagent type |
|----------|-----------|---------------|
| Claude Code | `Task` tool with `subagent_type: Explore` (read-only investigation) or `general-purpose` (when Explore unavailable) | Explore preferred — read-only enforced |
| Codex | `spawn_agent` with `agent_type: explorer` | Read-only by Codex contract |
| Droid | `spawn_agent` or platform-equivalent (verify tool name in current Droid docs) | Read-only |
| Fallback | Main thread sequential | Use when no subagent primitive is available |

Investigation subagents are **read-only**. They must not Edit, Write, Bash beyond Read / Grep / Glob, or git-mutate. Each returns a structured payload:

```yaml
entry_id: bug/runtime-errors/oauth-callback-2025-08-12
recommendation: Update | Keep | Consolidate | Replace | Delete
confidence: low | medium | high
evidence:
  - "file `src/auth/callback.ts` renamed to `src/auth/oauth/callback.ts` (git log shows move 2025-11-03)"
  - "function signature unchanged — solution still applies"
  - "no successor entry found"
open_questions:
  - "should this be consolidated with bug/runtime-errors/oauth-token-2025-09-04?"
```

When spawning subagents, include this directive in the task prompt:

> Use Read, Grep, Glob for all file investigation. Do NOT use shell commands (`ls`, `find`, `cat`, `grep`, `bash`) for file operations. This avoids permission prompts and is more reliable. Do NOT edit, create, or delete any files. Return only the structured evidence payload defined in the workflow.

The orchestrator (this skill, on the main thread) merges results, cross-references them in Phase 1.75, and executes all writes / deletes centrally.

For 1-2 entries, investigate on the main thread — no subagent overhead is worth it.

For Replace candidates, **investigation can be parallel; the actual replacement write is sequential** (one Replace at a time, see Phase 4).

### 1.3 — Investigation depth heuristics

- **Auto-Delete evidence** = `module` path missing AND no Grep hits for any class / function names mentioned in the body AND no successor pattern in the same domain. All three together = unambiguous Delete (code gone + problem domain gone). Two of three = Replace candidate. One of three = Update or Keep.
- **Cosmetic drift** (Update territory): file renamed, module field outdated, related-doc paths broken, but the solution body still describes how the code works today.
- **Substantive drift** (Replace territory): the body's recommended fix conflicts with current code, the architectural approach changed, or the preferred pattern is different. **The boundary:** if you find yourself rewriting the solution section or changing what the entry recommends, that is Replace, not Update.

Memory-sourced cross-signals are supplementary, not primary. A `related_to` reference suggesting a different approach does not alone justify Replace or Delete — corroborate against codebase evidence.

### Done when

- Every entry in scope has a recommendation, evidence list, confidence rating.
- All subagents (if dispatched) have returned and been merged.
- The orchestrator has the full investigation map: `{entry_id: {recommendation, evidence, confidence, open_questions}}`.

---

## Phase 1.75: Cross-doc analysis

**Goal:** catch problems visible only when comparing entries to each other — overlap, supersession, contradictions.

Group entries by `(module, category, primary tag)` triplet. For each pair within a group, compare:

- **Problem statement** — same underlying problem?
- **Solution shape** — same approach, even if worded differently?
- **Referenced files** — same code paths?
- **Root cause** — same cause identified?
- **Tags** — overlapping?

High overlap across 3+ dimensions is a strong **Consolidate** signal. The question to ask: "Would a future maintainer need to read both entries to get the current truth, or is one mostly repeating the other?"

### Supersession patterns

- Newer entry covers same files + same workflow + broader runtime behavior than older entry → older is consolidation candidate.
- Older entry describes a specific incident; newer entry generalizes it into a pattern → consolidate.
- Two entries recommend the same fix; newer one has better context, examples, or scope → consolidate.

### Conflict detection

Look for outright contradictions:

- Entry A says "always use X"; entry B says "avoid X".
- Entry A references a file that entry B says was deprecated.
- Entry A and entry B describe different root causes for the same observable problem.

Contradictions are more urgent than individual staleness — they actively confuse readers. Flag for immediate Consolidate (if one is a stale version of the same truth) or Update / Replace.

### Canonical entry pick (for Consolidate)

For each cluster identified as overlapping, pick the canonical entry:

- Most recent date.
- Broadest module scope.
- Highest-confidence Phase 1 recommendation.
- Cleanest body (no broken references).

The non-canonical entries either get merged (subsumed → unique content into canonical, then `git rm`) or marked redundant (delete-on-merge).

### Retrieval-value test

Before recommending two entries stay separate, apply: "If a maintainer searched for this topic six months from now, would having these as separate entries improve discoverability, or just create drift risk?"

Separate entries earn their keep only when:

- They cover genuinely different sub-problems.
- They target different audiences or contexts (e.g. one is debugging, another prevention).
- Merging would create an unwieldy entry harder to navigate than two focused ones.

Default to consolidate when none apply.

### Done when

- Every entry's classification accounts for cross-doc context.
- Consolidate clusters identified with canonical pick.
- Contradictions flagged.

---

## Phase 2: Classify

**Goal:** assign each entry exactly one of the 5 outcomes, applying [phases.md](phases.md) decision criteria.

For each entry, the recommendation from Phase 1 + cross-doc context from Phase 1.75 produces:

- **Keep** — accurate, no edit needed
- **Update** — references drifted; solution still correct
- **Consolidate** — overlaps heavily with another entry (canonical doc identified)
- **Replace** — guidance now misleading; successor needs writing
- **Delete** — code gone AND problem domain gone

### Replace evidence sufficiency check

Replace requires writing a trustworthy successor. Assess whether Phase 1 investigation gathered enough:

- **Sufficient** — you understand the old recommendation AND the current approach. File paths, current pattern, why old guidance is misleading. → proceed to Phase 4 Replace flow.
- **Insufficient** — the drift is so fundamental you can't confidently document the current approach. Entire subsystem replaced; new architecture too complex to summarize from a file scan. → mark stale (Phase 4 stale flow).

In autofix mode, "insufficient evidence" always routes to mark-stale, never to a half-baked Replace.

### Auto-Delete criteria (must meet ALL)

- The referenced files are gone (Glob confirms).
- No Grep hits for class / function names from the body.
- No successor pattern visible in the same problem domain.
- No `related_to` cross-reference points at this entry from other entries.

When all four conditions hold, classify as Delete and execute without asking (interactive too — it's unambiguous). When any fails, downgrade to Replace or mark stale.

### Done when

- Every entry has exactly one classification.
- Sufficiency check passed for every Replace; insufficient ones reclassified as mark-stale.
- Auto-Delete entries flagged as auto-applicable.

---

## Phase 3: Ask (interactive only)

**Goal:** confirm decisions with the user. Skip entirely in autofix mode.

### 3.1 — Group decisions to minimize friction

Bundle the easy ones, isolate the hard ones:

1. **Group obvious Keeps** — single batched confirmation: "These N entries reviewed without changes — proceed?"
2. **Group obvious Updates** — batched confirmation when the fixes are mechanical (path rename, module field update). "These N entries get straightforward reference updates — proceed?"
3. **Present Consolidate clusters individually** — show canonical doc + what merges + what gets deleted.
4. **Present Replace candidates individually** — show old guidance + current code finding + proposed successor outline.
5. **Present non-auto Delete cases individually** — show evidence, ask explicitly. Auto-Delete bypasses this.

### 3.2 — Question style

Use the platform's blocking-question tool:

| Platform | Tool |
|----------|------|
| Claude Code | `AskUserQuestion` (deferred — load via `ToolSearch select:AskUserQuestion` if not yet in scope) |
| Codex | `request_user_input` |
| Gemini | `ask_user` |
| Droid | `ask_user` or platform-equivalent |
| Fallback | Print numbered list, read typed reply |

Rules:

- **One question at a time.**
- **Multiple choice** when natural.
- **Lead with the recommendation** — don't enumerate all 5 outcomes if only 2 are plausible.
- **One-sentence rationale** — evidence is in the report, not the question.

Example question shape (single entry):

```
Entry: bug/runtime-errors/oauth-callback-2025-08-12
Evidence:
  - module `src/auth/callback.ts` renamed to `src/auth/oauth/callback.ts`
  - function signature unchanged
  - no successor entry found
Recommendation: Update (rename references)

Options:
  1. Update (recommended)
  2. Skip for now
  3. Mark stale
```

### 3.3 — Skip discoverability check until Phase 6

Phase 3 only handles per-entry decisions. The CLAUDE.md / AGENTS.md discoverability question runs in Phase 6 — separate, after the report exists.

### Done when

- User has confirmed every batched group and every individual item.
- Skipped items are recorded in the report.

---

## Phase 4: Execute

**Goal:** apply the decisions. Different flows per outcome.

### 4.1 — Keep flow

No edit. Record `reviewed-without-edit` in the report.

### 4.2 — Update flow

Agent edits the entry in place using the Write tool. **Frontmatter must round-trip** — preserve unknown fields (someone else's metadata on this entry must survive).

Pattern:

1. Read the file.
2. Parse frontmatter (split on the first two `---` lines).
3. Mutate only the specific fields that need updating (e.g. `module: <new path>`).
4. Re-emit frontmatter in the original key order if possible (PyYAML round-trip preserves it; stdlib parser preserves seen-fields order).
5. Write the file back atomically.

For frontmatter mutations the skill cannot guarantee round-trip on (entries with quirky YAML), prefer using the appropriate flowctl helper:

- `flowctl memory mark-stale <id>` — for stale-flagging (handles round-trip via existing `write_memory_entry`).
- `flowctl memory mark-fresh <id>` — for un-stale-flagging.

For body-only edits (code snippets, prose), Write is fine — frontmatter doesn't change.

### 4.3 — Consolidate flow

The orchestrator handles consolidation directly (no subagent — entries are already read, merge is a focused edit).

For each cluster from Phase 1.75:

1. **Confirm canonical entry** (already picked in 1.75).
2. **Extract unique content** from subsumed entries — anything the canonical doesn't already cover. Edge cases, alternative approaches, extra prevention rules.
3. **Merge into canonical** in a natural location. Don't append blindly — integrate where it logically belongs. Combine `tags` arrays (dedupe). Preserve canonical's `module`.
4. **Update `related_to` cross-references** in any other entries that pointed at the subsumed entries — re-point to canonical.
5. **`git rm` the subsumed entries.** Not archive — delete. Git history preserves them.

If a cluster has 3+ overlapping entries, process pairwise: consolidate the two most overlapping first, then evaluate whether the merged result should consolidate with the next.

### 4.4 — Replace flow

Process Replace candidates **one at a time, sequentially.** Each replacement may need significant code investigation to write the successor — running multiple in parallel risks orchestrator context exhaustion.

When evidence is sufficient (Phase 2 check):

1. Spawn a single subagent (sequential) to write the replacement entry. Pass:
   - The old entry's full content.
   - A summary of investigation evidence (what changed, what current code does, why old guidance misleads).
   - The target track + category (same as old entry unless category itself drifted).
   - The memory schema reference: required fields = `title`, `date`, `track`, `category`. Track-specific = `problem_type` / `symptoms` / `root_cause` / `resolution_type` for bug; `applies_when` for knowledge. Optional = `module`, `tags`, `related_to`. (See `MEMORY_REQUIRED_FIELDS` / `MEMORY_BUG_FIELDS` / `MEMORY_KNOWLEDGE_FIELDS` / `MEMORY_OPTIONAL_FIELDS` constants in `flowctl.py:3679-3696`.)
2. The subagent uses the Write tool OR `flowctl memory add --track <t> --category <c> --title "..." --body-file <path>` to land the file. Either works — flowctl `add` enforces schema validation; direct Write requires the subagent to emit valid frontmatter.
3. After the subagent completes, the orchestrator `git rm`'s the old entry. Optionally include `related_to: [<old-id>]` in the new entry's frontmatter for traceability.

When evidence is insufficient:

1. Mark the entry as stale: `flowctl memory mark-stale <id> --reason "<what was found>" --audited-by "/flow-next:audit"`.
2. Report what evidence was found and what's missing.
3. Recommend the user run a domain-specific solve afterwards to capture fresh context.

### 4.5 — Delete flow

```bash
git rm "$REPO_ROOT/.flow/memory/<entry-path>"
```

Do not archive. Do not move. Git history preserves every deleted file. Recovery: `git log --diff-filter=D -- .flow/memory/`.

Only execute Delete when ALL auto-Delete criteria hold (Phase 2 §Auto-Delete). Otherwise downgrade to Replace or mark-stale.

### 4.6 — Mark-stale flow (autofix ambiguous + Replace-insufficient)

```bash
"$FLOWCTL" memory mark-stale "$ENTRY_ID" \
  --reason "<one-line ambiguity description>" \
  --audited-by "/flow-next:audit"
```

The helper sets `status: stale`, stamps `last_audited` (today's date), records `audit_notes` from `--reason`. Atomic via existing `write_memory_entry` — preserves unknown frontmatter fields.

### Done when

- Every classified entry has been acted on (or skipped, in interactive mode with user consent).
- All deletions and merges are staged in git.
- All edits land via Write or flowctl helper.

---

## Phase 5: Report + Commit

**Goal:** print the full report. Commit changes if any. Detect git context first; ask in interactive, default sensibly in autofix.

### 5.1 — Report structure

Print to stdout as markdown. The report is the deliverable — do not summarize internally.

```text
Memory Audit Summary
====================
Scanned: <TOTAL> entries
Skipped legacy: <LEGACY_ENTRY_COUNT> (run `/flow-next:memory-migrate` first to make these auditable)

Kept: <X>
Updated: <Y>
Consolidated: <C>  (clusters: <K>)
Replaced: <Z>
Deleted: <W>
Marked stale: <S>
Skipped (no decision): <U>
```

Then per-entry detail (one block each):

```
- <entry_id>
  Classification: <Keep|Update|Consolidate|Replace|Delete|Stale>
  Evidence:
    - <bullet>
    - <bullet>
  Action: <what was done — file edits, deletions, mark-stale calls>
  [Consolidate only] Canonical: <entry_id>; merged: [<list>]; deleted: [<list>]
  [Replace only] Old guidance: <one-line>; New entry: <new_id>
```

For **Keep** outcomes, group under a "Reviewed without edits" subsection so the result is visible without git churn.

### 5.2 — Autofix two-section split

In autofix mode, split actions into:

- **Applied** — writes that succeeded.
- **Recommended** — actions that could not be written (e.g. permission denied, schema validation failed). Same detail as Applied; framed for a human to apply manually.

If all writes succeed, Recommended is empty. If no writes succeed (read-only invocation), all actions land under Recommended — the report becomes a maintenance plan.

### 5.3 — Detect git context

```bash
GIT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")
GIT_DIRTY=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | grep -v "^??" | wc -l | tr -d ' ')
GIT_DEFAULT=$(git -C "$REPO_ROOT" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null \
  | sed 's|^origin/||' || echo "main")
```

Skip Phase 5 commit logic if no files were modified (all Keep, all writes failed).

### 5.4 — Interactive commit options

If `GIT_BRANCH` matches `main` / `master` / `$GIT_DEFAULT`:

```
1. Create a branch + commit + open PR (recommended)
   Branch: docs/audit-memory-<date>  (or topic-specific if scope was narrow)
2. Commit directly to <GIT_BRANCH>
3. Don't commit — I'll handle it
```

If `GIT_BRANCH` is a feature branch + clean tree:

```
1. Commit to <GIT_BRANCH> as a separate commit (recommended)
2. Create a separate branch + commit
3. Don't commit
```

If `GIT_BRANCH` is a feature branch + dirty tree (other uncommitted changes):

```
1. Commit only audit changes to <GIT_BRANCH> (selective staging)
2. Don't commit
```

**Stage only audit-modified files**, regardless of which option the user picks — never `git add -A` from this skill.

### 5.5 — Autofix commit defaults

| Context | Default action |
|---------|---------------|
| On main/master/default | Create branch `docs/audit-memory-<date>`, commit, attempt `gh pr create`. If PR creation fails, report the branch name |
| On feature branch | Commit as a separate commit on the current branch |
| Git operations fail | Include the recommended git commands in the report and continue |

Stage only audit-modified files.

### 5.6 — Commit message

Descriptive, concise, follows repo conventions (check `git log -5 --oneline` for style):

```
audit(memory): update 3 entries, consolidate 2, mark 1 stale

- Updated: bug/runtime-errors/oauth-callback (path rename)
- Consolidated: bug/integration/{a, b} → b
- Marked stale: knowledge/conventions/legacy-deploy (insufficient successor evidence)
```

### Done when

- Full report printed to stdout.
- Commit lands (or user explicitly declined / autofix logged a recommendation).

---

## Phase 6: Discoverability check

**Goal:** verify the substantive CLAUDE.md / AGENTS.md mentions `.flow/memory/` semantically — schema basics + when to consult. Add a minimal line if missing.

This runs every time, at the end of the audit. The knowledge store only compounds value when agents can find it.

### 6.1 — Identify the substantive file

```bash
HAS_CLAUDE=$([[ -f "$REPO_ROOT/CLAUDE.md" ]] && echo 1 || echo 0)
HAS_AGENTS=$([[ -f "$REPO_ROOT/AGENTS.md" ]] && echo 1 || echo 0)
```

If neither exists, skip the check entirely — there's nothing to amend.

If both exist, read each. The substantive file is the one that's NOT just an `@`-include shim:

- A file containing only `@CLAUDE.md` (or similar single-line `@`-include) is a shim.
- The other file holds the substantive content. Edit there.

If both look substantive (rare), pick `CLAUDE.md` as the conventional primary.

### 6.2 — Semantic assessment

Read the substantive file. Decide whether an agent reading it would learn three things:

1. **A searchable knowledge store of past learnings exists** under `.flow/memory/`.
2. **Enough about its structure to search effectively** — categorized tree (`bug/<category>/` + `knowledge/<category>/`), YAML frontmatter (`track`, `category`, `module`, `tags`, `status`).
3. **When to consult it** — before implementing features in a documented module, when debugging a class of issue with prior art, when making decisions in a known-discussed area.

This is **semantic**, not a string match. The information could be:

- A line in an architecture / directory-listing section.
- A bullet in a gotchas section.
- Spread across multiple places.
- Expressed without ever using the literal path `.flow/memory/`.

Use judgment: would an agent reasonably discover and use the memory store after reading the file? If yes, the check passes — no edit.

### 6.3 — Draft addition (when missing)

When the spirit isn't met, draft the smallest addition that communicates the three things. Match the file's existing style and density.

**Calibration examples** (adapt to the file — these are not templates):

When there's an existing directory listing or architecture section, add a line:

```
.flow/memory/  # categorized learnings (bug/<category>/, knowledge/<category>/) — YAML frontmatter (track, category, module, tags, status); search via `flowctl memory search <q>`; relevant when implementing or debugging in documented modules
```

When nothing in the file is a natural fit, a small headed section is appropriate:

```
## Memory store

`.flow/memory/` — categorized learnings from past work. Tree:
`bug/<category>/<slug>-<date>.md` + `knowledge/<category>/<slug>-<date>.md`.
YAML frontmatter (`track`, `category`, `module`, `tags`, `status`). Search via
`flowctl memory search <q>`. Relevant when implementing or debugging in modules
that may have documented prior art.
```

Keep tone informational, not imperative. "Relevant when" beats "always check before". Imperative directives cause redundant reads when a workflow already has dedicated search steps.

### 6.4 — Apply (interactive: ask consent; autofix: recommend only)

**Interactive:**

Show the proposed addition + where it would land. Ask via blocking-question tool:

```
CLAUDE.md does not mention .flow/memory/.
Future agents (other tools, fresh sessions) won't know to consult past learnings
when working in documented modules.

Proposed addition (under <section name>):
<draft text>

Options:
  1. Apply addition (recommended)
  2. Edit the draft first
  3. Skip — I'll handle it
```

If the user picks Apply:

- Edit the file via Edit tool.
- Stage + commit. If Phase 5 already committed, either amend (same branch, no push yet) or create a follow-up commit (`docs: surface .flow/memory/ in CLAUDE.md`).
- If Phase 5 pushed a branch to remote, push the follow-up commit too so the open PR includes it.

If the user picks Edit, accept the revised text and apply.

If the user picks Skip, leave the file untouched. Surface as "Discoverability recommendation" in the report so it's visible.

**Autofix:**

Do not edit instruction files. Surface as a "Discoverability recommendation" line at the end of the report:

```
Discoverability: CLAUDE.md does not mention .flow/memory/. Recommended addition:
<draft text>
```

Autofix scope is memory entries, not project config — instruction-file edits need human-in-the-loop consent.

### 6.5 — Commit handling

If step 6.4 produced an instruction-file edit AND Phase 5 already committed audit changes:

- Same branch, no push yet → amend or follow-up commit (skill picks based on `git status` cleanliness).
- Same branch, pushed to remote → follow-up commit, push so the open PR sees the change.
- User picked "Don't commit" in Phase 5 → leave the instruction-file edit unstaged alongside other audit changes. No separate commit logic.

### Done when

- Substantive instruction file assessed.
- If missing, a minimal addition is either applied (interactive consent) or surfaced as a recommendation (autofix or skip).
- Commit / push synced with Phase 5's path.

---

## Manual smoke (acceptance R3, R4, R5, R6, R11)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:audit` in a real session. Expected behavior:

- Phase 0 walks `.flow/memory/`, lists per-cluster counts, reports legacy skip count if `pitfalls.md` etc. exist.
- Phase 1 produces evidence per entry. For 3+ entries, parallel investigation subagents run.
- Phase 2 classifies; Replace candidates with insufficient evidence reclassify as mark-stale.
- Phase 3 (interactive) groups Keeps / Updates for batched confirmation; presents Consolidate / Replace / Delete individually via blocking-question tool.
- Phase 4 executes via Write / `flowctl memory mark-stale` / `git rm`.
- Phase 5 prints the report; offers commit options based on git context.
- Phase 6 checks CLAUDE.md / AGENTS.md for `.flow/memory/` mention; offers minimal addition if missing.

In autofix mode (`/flow-next:audit mode:autofix`), Phase 3 is skipped, ambiguous entries are marked stale, and the report is the sole deliverable.

If Phase 0 produces nothing (no categorized entries, only legacy), the skill exits cleanly with the legacy-skip count.
