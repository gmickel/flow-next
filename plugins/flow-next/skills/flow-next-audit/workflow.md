# /flow-next:audit workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
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

For each kept path, read the frontmatter (parser pattern from `prospect/workflow.md` §0.2 — stdlib Python is fine; PyYAML when available is nicer). Capture: `entry_id` (from path), `track`, `category`, `slug`, `date`, `title`, `module`, `tags`, `status`, `last_audited` (empty when never audited — drives the §0.75 change-detection pre-filter), plus the body for later investigation.

If the entry's `status` is `stale` already, surface it in the report under "Already stale" and skip investigation in autofix mode (mark-stale is idempotent — re-marking adds noise). In interactive mode, offer to refresh-investigate (rare path; user-driven).

If the entry's `status` is `hardened`, capture its `hardened_into` value into the entry record. Hardened entries are **not** dropped from the walk: they get the cheap gate-liveness check in §0.75, never a full re-investigation. Note that `flowctl memory list` excludes hardened entries by default (same treatment as stale) — the audit's own Glob walk in §0.1 sees them regardless, which is why the walk, not `memory list`, is the source of truth here.

**Decisions are auto-walked.** `MEMORY_CATEGORIES["knowledge"]` includes `decisions` (fn-38 schema extension), so the glob in §0.1 picks up `.flow/memory/knowledge/decisions/*.md` automatically — no separate phase. Decision entries get a calibrated judging question and a different `Replace` shape; see [phases.md](phases.md) §Decision-entry calibration. Decision-specific frontmatter (`decision_status`, `superseded_by`, `alternatives_considered`) is captured into the entry record for Phase 1 to use; entries with `decision_status: superseded` are surfaced as historical record and skipped (the audit target is the successor, not the superseded entry).

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

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

### 0.3 — Apply scope hint (when present)

When `SCOPE_HINT` is empty, every discovered entry stays in scope — skip this step and go to §0.4.

When `SCOPE_HINT` is non-empty, read [references/scope-narrowing.md](references/scope-narrowing.md) and execute its `0.3 — Apply scope hint` section — it owns the five-step first-match-wins narrowing order (track, category, module, tag, title / body keyword), the strategy print, and the zero-match handling (interactive asks widen / re-enter / abort; autofix prints and exits cleanly).

### 0.4 — Count + route

Count remaining entries (`TOTAL`). Route:

| TOTAL | Path | Notes |
|-------|------|-------|
| 0 | exit cleanly | Print `No categorized memory entries found.` plus legacy skip note if any |
| 1-2 | **Focused** | Investigate directly, then present recommendation(s) |
| 3-8 | **Batch** | Investigate (parallel subagents on 3+), then present grouped recommendations |
| 9+ | **Broad** | Triage first: pick highest-impact cluster, recommend starting there (interactive) or process all clusters in impact order (autofix) |

### 0.5 — Broad-scope triage (only when `TOTAL >= 9`)

When `TOTAL < 9`, there is nothing to triage — the route picked in §0.4 stands.

When `TOTAL >= 9`, read [references/scope-narrowing.md](references/scope-narrowing.md) and execute its `0.5 — Broad-scope triage` section — it owns the `(module, category)` clustering, the `cluster_score` formula, the interactive top-cluster-plus-two-alternatives question, and the autofix impact-ordered queue print.

### Done when

- `ENTRIES` (the in-memory list) is finalized for this run.
- Legacy skip count is captured for the eventual report.
- `MODE` × `TOTAL` × `SCOPE` resolution is clear (route picked).

---

## Phase 0.5: Glossary scan

**Goal:** for every glossary file on the ancestor chain, verify each term has at least one usage in tracked code (term itself or any `_Avoid_` alias). Mark stale on absence; surface alias-creep as a Phase 3 signal.

This phase runs in parallel concept to the memory walk — same audit invocation, separate scope. Glossary files are project state (not flow-next bookkeeping; see fn-38 R18). Skip the phase entirely when `flowctl glossary list --json` reports zero files.

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$("$FLOWCTL" glossary list --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '(.file_count // 0) > 0' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/glossary-scan.md, then continue with Phase 0.75."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, STOP and Read [references/glossary-scan.md](references/glossary-scan.md) before any further step, then execute it — it owns the enumeration and JSON shape, the per-term code search and its decision table, Edit-tool stale-marking, husk advisories, alias-creep handling, the four glossary report counts, and the §4.4.1 Phase-4 execution half. Then continue with Phase 0.75. When the gate is silent (no glossary files on the ancestor chain), continue — nothing fires here, the glossary report counts are all zero, and §4.4.1 has nothing to execute.

### Done when

- The glossary gate has been evaluated, and — when it fired — the reference's own `Done when` is satisfied.

---

## Phase 0.75: Change-detection pre-filter — investigate only what changed

**Goal:** a mature store re-audited from scratch dispatches a Phase-1 investigation subagent *per entry*, even for entries whose referenced code hasn't moved since the last audit. Those are still current — auto-Keep them without investigation. This turns the dominant runtime cost from **O(all entries) → O(changed)** and concentrates the model's attention on entries with an actual drift signal.

### 0.75.1 — Recurrence pre-scan (runs BEFORE the auto-Keep decision)

**Order matters, and it is load-bearing for Harden.** Auto-Keep below excludes unchanged-module entries from Phase 1 entirely. The entries most likely to deserve a gate are exactly the old, settled, repeatedly re-taught ones whose module stopped moving long ago — so gathering recurrence evidence inside Phase 1 would guarantee those entries are never seen. Gather it here instead, before anything is auto-Kept. The cost is three cheap file-local commands per entry, no code investigation:

```bash
# per entry: $entry_file (path from §0.1), $entry_id
# `grep -c` PRINTS 0 and EXITS 1 on zero matches — a `|| echo 0` fallback would append a
# SECOND zero and break the later numeric comparison. Swallow the exit status instead.
UPDATE_HEADINGS=$(grep -c '^## Update ' "$entry_file" 2>/dev/null || true)
UPDATE_HEADINGS=${UPDATE_HEADINGS:-0}
# SUBSTANTIVE commits only — a raw `git log | wc -l` counts the audit's OWN bookkeeping
# (every `mark-fresh` / `mark-stale` / `mark-hardened` rewrites `last_audited` & friends), so
# in a repo that commits its audits three routine sweeps alone would clear the >= 4 threshold
# and permanently bypass auto-Keep. One git call per entry; awk drops commits whose diff on
# this file touches ONLY frontmatter bookkeeping fields.
# `--follow` is REQUIRED: memory entries get moved (`flowctl memory migrate` relocates legacy
# flat files into categorized paths; consolidation renames entries), and a path-limited log
# stops dead at the rename — the pre-rename history vanishes and the entry silently falls
# below the threshold, suppressing a Harden candidate. `--follow` takes exactly ONE pathspec
# (`fatal: --follow requires exactly one pathspec` otherwise) — this scan is single-file, so
# never add a second path here. A PURE rename emits `similarity index` / `rename from` /
# `rename to` lines and no `+`/`-` content, so awk correctly does not count a `git mv` as a
# re-teaching; a rename carrying real edits still counts once, as it should.
ENTRY_COMMITS=$(git -C "$REPO_ROOT" log --follow --format='COMMIT %H' --patch --unified=0 \
  -- "$entry_file" 2>/dev/null | awk '
  /^COMMIT /        { substantive = 0; next }        # new commit — reset the per-commit flag
  /^(--- |\+\+\+ )/ { next }                         # skip file headers, not content
  /^[+-]/ {
    field = substr($0, 2)
    if (field ~ /^(last_audited|audit_notes|status|stale_reason|stale_date|hardened_into):/) next
    if (!substantive) { substantive = 1; count++ }
  }
  END { print count + 0 }')                          # prints 0 for an untracked/new file
ENTRY_COMMITS=${ENTRY_COMMITS:-0}
# plus, from the frontmatter already parsed in §0.1: related_to length, last_updated
```

An entry is **recurrence-qualified** when `UPDATE_HEADINGS >= 2` OR `ENTRY_COMMITS >= 4`.

`ENTRY_COMMITS` counts only commits that changed the lesson itself — the entry-creation commit and every later body/reference edit, **across renames** (`--follow`). Audit-stamp commits are not evidence the lesson was re-taught, and counting them would make the store's recurrence signal grow with audit diligence rather than with recurring pain, collapsing the O(changed) pre-filter over time. A `git mv` is not a re-teaching either — it neither counts as a substantive commit nor truncates the history behind it.

A `related_to` **cluster** qualifies only as a corroborated whole, never on size alone: a cluster of `>= 3` entries qualifies when **any member** has at least one `## Update` heading, or **any member** meets the commit signal. Cluster aggregates must therefore be computed here too, before anything is auto-Kept — a cluster whose members all have unchanged modules would otherwise be auto-Kept entry-by-entry and never seen:

```bash
# per related_to cluster: sum/max the per-entry values gathered above
CLUSTER_SIZE=<number of entries in the related_to cluster>
CLUSTER_MAX_UPDATES=<max UPDATE_HEADINGS across members>
CLUSTER_MAX_COMMITS=<max ENTRY_COMMITS across members>
# qualified when: CLUSTER_SIZE >= 3 AND (CLUSTER_MAX_UPDATES >= 1 OR CLUSTER_MAX_COMMITS >= 4)
```

A bare `related_to >= 3` with no `## Update` anywhere and no member meeting the commit signal **proposes nothing** — see [phases.md](phases.md) §Harden for the thresholds and the calibration evidence behind them.

- **Recurrence-qualified → bypass auto-Keep.** The entry — or, for a qualified cluster, **every member of that cluster** — enters the Phase-1 investigation set for Harden consideration even when its module is unchanged. Record why: `recurrence bypass — 2 Update headings, module unchanged`, or `recurrence bypass — cluster of 4, 1 Update heading on <member-id>`.
- Not qualified → fall through to the normal auto-Keep decision below.

A qualified cluster is evaluated as **one** Harden unit (Consolidate first, per the precedence rule) — the whole cluster is investigated so the merge can happen, but it never yields one gate per member.

Recurrence is inferred from these **write-side artifacts plus LLM judgment**. There is no read-side usage telemetry anywhere in flow-next: `memory-scout` retrieval and worker re-anchor reads leave no trace on the entry, and nothing records that an entry fired during a run. Do not claim a usage count in evidence bullets — cite the artifacts.

### 0.75.2 — Hardened entries: gate-liveness check only

An entry with `status: hardened` skips both auto-Keep and full investigation. Instead, grep the `<path>` from its `hardened_into` for the `<rule-id>` **verbatim, as a literal substring** (that is the contract §4.7 composes against), and apply the same activeness check as Phase 4's verification (resolved lint config, live CI job, substantive instruction file):

- **Gate present and active** → report as still-hardened. No investigation, no write.
- **Gate gone or inactive** → propose un-graduation via `flowctl memory mark-fresh "$entry_id"` (returns the entry to `active` and drops `hardened_into`), citing which surface was checked and what was missing. Interactive asks in Phase 3; autofix reports it under Recommended without applying.
- **Gate upgraded** (a better surface now enforces the class) → re-`mark-hardened` with the new ref; it is idempotent and replaces `hardened_into`.

Without this check a reverted lint rule would strand the lesson permanently: excluded from default `memory list` / `search` (so memory-scout never re-injects it) with no path back.

### 0.75.3 — Auto-Keep decision

For each remaining discovered entry (§0.1) — not recurrence-qualified, not hardened — decide whether it needs Phase-1 investigation:

```bash
# per entry: $entry_id, $module (frontmatter), $last_audited (frontmatter, may be empty),
# $entry_status (the entry's `status` field — NOT named `status`: that is a read-only reserved
# variable in zsh, which the skills' bash blocks run under; a bare `status=` assignment errors).
NEEDS_INVESTIGATION=1
if [[ -n "$module" && -n "$last_audited" && "$entry_status" != "stale" && -e "$module" ]]; then
  # $module must be a real tracked path for this to be sound: a logical module NAME, or a
  # DELETED module (path gone → a Delete candidate), both fail `-e` and fall through to investigation.
  CHANGED="$(git log --oneline --since="$last_audited" -- "$module" 2>/dev/null | head -1)"
  [[ -z "$CHANGED" ]] && NEEDS_INVESTIGATION=0   # module path untouched since the last audit → still current
fi
```

- `NEEDS_INVESTIGATION=0` (has `last_audited`, `module` is an existing tracked path, zero commits to it since, not already `stale`) → **auto-Keep**: `flowctl memory mark-fresh "$entry_id"` (re-stamps `last_audited`), record `auto-Kept — <module> untouched since <last_audited>` in the Phase-5 report, and **exclude the entry from the Phase-1 investigation set**.
- Otherwise (never audited → no `last_audited`; no `module` or a logical name → can't change-detect; module path gone → possible Delete; module changed; or already `stale`) → keep it in the Phase-1 investigation set.

**Auto-Kept entries still flow into Phase 1.75 cross-doc analysis and the Phase-5 report.** An auto-Kept entry missing from the contradiction scan or from the report has broken this — the pre-filter skips only the expensive per-entry investigation, never the cheap pairwise contradiction scan, so an entry that went stale because a *different* entry changed is still caught. Autofix always applies the pre-filter; interactive mode may offer "re-investigate all anyway" (rare, user-driven).

A recurrence-qualified entry (§0.75.1) is never auto-Kept, even when its module is untouched.

### Done when

- Every discovered entry carries a recurrence verdict from §0.75.1 (qualified, with the reason recorded, or not).
- Every `status: hardened` entry has its gate-liveness result (still-hardened / un-graduation proposal / re-`mark-hardened`).
- Every remaining entry is either auto-Kept (stamped `mark-fresh`, reason recorded for the Phase-5 report) or in the Phase-1 investigation set.

## Phase 1: Investigate (per entry)

**Goal:** for each entry in scope, verify its claims against the current codebase and form a recommendation with evidence.

A memory entry has dimensions that can independently go stale:

- **References** — do the file paths, modules, and symbols mentioned in the body or `module` field still exist? If renamed, where did they move?
- **Solution** — does the recommended fix still match how the code actually works today? A file rename with a completely different implementation pattern is not just a path update.
- **Code examples** — if the body includes code snippets, do they reflect current implementation?
- **Related entries** — `related_to: [<id>, ...]` cross-references — do those entries still exist? Are they consistent?
- **Problem domain** — does the application still face the problem this entry solves? A bug entry about a deleted feature is misleading.
- **Recurrence** — is this lesson being re-taught rather than absorbed? Carried in from the §0.75.1 pre-scan (`## Update` heading count, entry-file commit count, `related_to` size). Recurrence plus mechanizability is the Harden signal.

### 1.1 — Per-entry investigation steps

For each entry:

1. **Read** the file (already loaded in Phase 0; re-read body if it was elided).
2. **Verify the `module` field** — Glob for the path. If missing, Glob for the basename across the repo (renamed?). Grep for any class / function names mentioned in the body.
3. **Verify referenced files** in the body — same pattern. List broken references.
4. **Check git log** in the affected area (if the path resolves): `git log --oneline -10 -- <path>`. Recent activity = code is alive; long quiet = candidate for deletion if also unreferenced elsewhere.
5. **Search for successor patterns** — if the entry is a bug, Grep for the symptom keywords in the current codebase. If matches turn up in code that looks like a re-implementation, the problem domain may persist under a new shape (Replace, not Delete).
6. **Carry the recurrence artifacts** from the §0.75.1 pre-scan into the evidence (`## Update` heading count, entry-file commit count, `related_to` size). **State them as artifacts, never as a usage count** — there is no read-side telemetry; nothing records that an entry fired during a run, so recurrence is inference over write-side artifacts plus judgment. For a recurrence-qualified entry, additionally judge **mechanizability** (is the lesson a deterministic check a gate could run?) and, if yes, discover which gate surfaces exist in this repo — an existing linter config, an existing CI workflow, the substantive instruction file. Never assume a surface; never scaffold one.
7. **Form a recommendation:** Keep / Update / Consolidate / Replace / Delete / Harden + 2-4 evidence bullets + confidence (low / medium / high). Apply the precedence rule in [phases.md](phases.md) — correctness (Replace / Delete) wins over Consolidate, which wins over Harden.

Match investigation depth to entry specificity. An entry referencing exact file paths and code snippets needs more verification than one describing a general principle.

### 1.2 — Subagent dispatch (3+ independent entries)

When `TOTAL >= 3` AND the entries don't share heavy overlap (different modules / categories), dispatch parallel investigation subagents. Pick the primitive that exists in your harness:

| Platform | Primitive | Subagent type |
|----------|-----------|---------------|
| Claude Code | `Task` tool with `subagent_type: Explore` (read-only investigation) or `general-purpose` (when Explore unavailable) | Explore preferred — read-only enforced |
| Codex | `spawn_agent` with `agent_type: explorer` | Read-only by Codex contract |
| Droid | `spawn_agent` or platform-equivalent (verify tool name in current Droid docs) | Read-only |
| Cursor | Host's generic subagent dispatch (no Explore/general-purpose builtins — only the plugin's own agents register) | Disallow Edit/Write in the prompt |
| Fallback | Main thread sequential | Use when no subagent primitive is available |

Investigation subagents are **read-only**. They must not Edit, Write, Bash beyond Read / Grep / Glob, or git-mutate. Each returns a structured payload:

```yaml
entry_id: bug/runtime-errors/oauth-callback-2025-08-12
recommendation: Update | Keep | Consolidate | Replace | Delete | Harden
confidence: low | medium | high
evidence:
  - "file `src/auth/callback.ts` renamed to `src/auth/oauth/callback.ts` (git log shows move 2025-11-03)"
  - "function signature unchanged — solution still applies"
  - "no successor entry found"
recurrence:            # carried from §0.75.1; artifacts only, never a usage count
  update_headings: 2
  entry_commits: 4
  related_to: 0
mechanizable: yes | no | n/a   # required whenever recommendation is Harden
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

**Goal:** assign each entry exactly one of the 6 outcomes, applying [phases.md](phases.md) decision criteria.

For each entry, the recommendation from Phase 1 + cross-doc context from Phase 1.75 produces:

- **Keep** — accurate, no edit needed
- **Update** — references drifted; solution still correct
- **Consolidate** — overlaps heavily with another entry (canonical doc identified)
- **Replace** — guidance now misleading; successor needs writing
- **Delete** — code gone AND problem domain gone
- **Harden** — correct, recurring (§0.75.1 signal) AND mechanizable; graduate into a gate and demote the entry to a pointer

### Outcome precedence (when several apply)

Apply [phases.md](phases.md) §Outcome precedence: **correctness (Replace / Delete) > Consolidate > Harden**. A wrong lesson is never graduated into a gate, and a `related_to` cluster is consolidated before the merged entry is considered — the cluster, not each member, is the Harden unit. An entry classified Consolidate this run may be re-evaluated for Harden once, as the merged canonical entry.

### Harden gate (both conditions required)

**A Harden classification rests on two independent conditions.** A Harden proposed on one of them alone has broken this: it needs both a recurrence signal from §0.75.1 (`>= 2` `## Update` headings or `>= 4` entry-file commits; `related_to >= 3` corroborates only) and an LLM judgment that the lesson is mechanizable. Missing either → Keep. The duplication guard runs before the candidate reaches Phase 3: an already-enforced-and-active class becomes a pointer-demotion proposal with no new artifact; a matched-but-inactive rule is a broken gate, so the entry stays `active` and the finding is reported. **In autofix mode, Harden candidates are never applied** — they are classified and reported under Recommended only.

### Replace evidence sufficiency check

Replace requires writing a trustworthy successor. Apply the **Evidence sufficiency check** in [phases.md](phases.md) §Replace (the gate): sufficient → Phase 4 Replace flow; insufficient → Phase 4 stale flow. In autofix mode, "insufficient evidence" always routes to mark-stale, never to a half-baked Replace.

### Auto-Delete criteria (all four required)

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

**Autofix (`MODE=autofix`):** skip this phase — no questions, no batching, no Harden accept. Genuinely ambiguous classifications were already routed to mark-stale in Phase 2; Harden candidates, un-graduation proposals, and glossary alias-creep findings carry straight into the Phase-5 Recommended bucket. Go to Phase 4.

**Interactive (`MODE=interactive`):** STOP and Read [references/interactive-ask.md](references/interactive-ask.md) before any further step, then execute it — it owns the grouping rules (batch obvious Keeps and obvious Updates; present Consolidate / Replace / non-auto Delete / Harden / un-graduation individually), the question-style rules, the example question shapes, the Harden candidate question (gate type, the draft artifact exactly as it would be written, evidence, and accept / different-gate-type / decline), and the deferral of the discoverability question to Phase 6.

### Done when

- Autofix: nothing runs here.
- Interactive: the reference's own `Done when` is satisfied — the user has confirmed every batched group and every individual item, and skipped items are recorded in the report.

---

## Phase 4: Execute

**Goal:** apply the decisions. Different flows per outcome.

### 4.1 — Keep flow

No content edit — but **stamp `flowctl memory mark-fresh "$entry_id"`** and record `reviewed-without-edit` in the report. The stamp re-sets `last_audited` to today (idempotent — mark-fresh on a non-stale entry just stamps the date), so the next audit's §0.75 change-detection pre-filter can skip this entry for free while its module stays untouched. Without the stamp, every Keep re-investigates from scratch on every future run (the O(all)-not-O(changed) cost §0.75 exists to remove).

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

Execute per [phases.md](phases.md) §Replace — the authoritative copy:

- Evidence **sufficient** (Phase 2 check) → §Replace "Action steps (sufficient evidence)".
- Evidence **insufficient** → §Replace's mark-stale fallback (same helper as §4.6).
- `knowledge/decisions/` entries → §"Replace = supersede": the old entry is **never** `git rm`'d — decision history stays on disk (round-trip rules from §4.2 apply when editing its frontmatter).

### 4.4.1 — Glossary stale-marking (Phase 0.5 outcomes)

Runs only when the Phase 0.5 gate fired. The steps live in [references/glossary-scan.md](references/glossary-scan.md) §4.4.1 — already loaded on that path. When the gate was silent there are no glossary outcomes to execute.

### 4.5 — Delete flow

```bash
git rm "$REPO_ROOT/.flow/memory/<entry-path>"
```

Do not archive. Do not move. Git history preserves every deleted file. Recovery: `git log --diff-filter=D -- .flow/memory/`.

**Delete executes only when all four auto-Delete criteria hold** (Phase 2 §Auto-Delete). A `git rm` on an entry that met three of the four has broken this — that entry downgrades to Replace or mark-stale.

### 4.6 — Mark-stale flow (autofix ambiguous + Replace-insufficient)

Execute per [phases.md](phases.md) §"Mark stale (autofix ambiguous + Replace-insufficient)" — the `flowctl memory mark-stale` helper with `--reason` + `--audited-by "/flow-next:audit"`. Never hand-edit frontmatter for stale-flagging; the helper is atomic and preserves unknown fields.

### 4.7 — Harden flow (interactive only — autofix never applies)

**Autofix stops here.** In `mode:autofix` no gate artifact is written and no entry is demoted; candidates go straight to the Phase-5 Recommended bucket carrying the full detail a human needs — gate type, the draft artifact, the recurrence evidence, and the `--gate-ref` that would be recorded. Un-graduation proposals (§0.75.2) are likewise Recommended-only.

**Interactive, and only after an explicit accept in Phase 3:** STOP and Read [references/harden-flow.md](references/harden-flow.md) before any further step, then execute it — it owns the one-at-a-time sequential processing, the artifact write, the per-gate-type verification that is a **hard precondition of demotion** (verification failure leaves the entry `active`, does NOT call `mark-hardened`, and reports a failed graduation), the `flowctl memory mark-hardened --gate-ref "<path>#<rule-id> -- <note>"` demotion with its literal-substring rule for `<rule-id>`, the pointer-demotion shortcut, and the `mark-fresh` un-graduation command. **Never `git rm` on Harden — on any track.**

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
Hardened: <H>  (failed graduations: <HF>; un-graduated: <HU>)
Marked stale: <S>
Skipped (no decision): <U>

Glossary
--------
Files scanned: <file_count> (<husk_count> husks)
Terms scanned: <total_terms>
Kept: <glossary_kept>
Marked stale: <glossary_marked_stale>
Alias-creep flagged: <glossary_alias_creep>
```

Then per-entry detail (one block each):

```
- <entry_id>
  Classification: <Keep|Update|Consolidate|Replace|Delete|Harden|Stale>
  Evidence:
    - <bullet>
    - <bullet>
  Action: <what was done — file edits, deletions, mark-stale calls>
  [Consolidate only] Canonical: <entry_id>; merged: [<list>]; deleted: [<list>]
  [Replace only] Old guidance: <one-line>; New entry: <new_id>
  [Decision Replace] Successor: <new_id>; old marked decision_status=superseded (NOT git-rm'd)
  [Harden only] Gate type: <lint|CI|instruction file>; Artifact: <path>;
                Gate-ref: <path>#<rule-id> -- <note>; Verified: <how it was confirmed live>
  [Harden — pointer only] Existing gate: <path>#<rule-id>; no new artifact written
  [Harden — failed] Gate type: <...>; Artifact: <path>; FAILED VERIFICATION: <reason>;
                    entry left active, not demoted
  [Un-graduated] Gate <path>#<rule-id> no longer live (<what was missing>); mark-fresh applied
```

For **Keep** outcomes, group under a "Reviewed without edits" subsection so the result is visible without git churn.

Hardened entries carried over from earlier runs whose gate is still live are listed under a "Still hardened" subsection — one line each (`<entry_id> → <gate-ref> (gate live)`), no evidence block, since they were not re-investigated.

Then per-glossary-term detail (only for stale + alias-creep cases — Keep is silent):

```
- <relative-path>:<term>
  Outcome: <Marked stale|Alias-creep|Marked stale + alias-creep>
  Term hits: <N>
  Alias hits: <alias-1>: <N1>, <alias-2>: <N2>
  Action: <Edit applied|None — recommendation only>
```

Husk advisories (one per file with `count: 0`) follow under a "Glossary husks" subsection.

### 5.2 — Autofix two-section split

In autofix mode, split actions into:

- **Applied** — writes that succeeded.
- **Recommended** — actions that could not be written (e.g. permission denied, schema validation failed). Same detail as Applied; framed for a human to apply manually.

If all writes succeed, Recommended is empty. If no writes succeed (read-only invocation), all actions land under Recommended — the report becomes a maintenance plan.

**Harden always lands under Recommended in autofix**, never under Applied — not because a write failed, but because autofix never attempts one. Each candidate carries the same detail a human needs to act: gate type, the draft artifact, the recurrence evidence, and the `--gate-ref` that would be recorded. Un-graduation proposals (a hardened entry whose gate is gone) are likewise Recommended-only. The `Hardened:` count is therefore `0` in autofix; the candidates show as `Harden candidates (recommended): <N>`.

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

- Phase 0 walks `.flow/memory/`, lists per-cluster counts, reports legacy skip count if `pitfalls.md` etc. exist. Decision entries (`knowledge/decisions/`) are picked up automatically once the schema extension lands (fn-38 task 1).
- Phase 0.5 walks every `GLOSSARY.md` on the ancestor chain via `flowctl glossary list --json`, greps tracked code per-term + per-`_Avoid_` alias, marks zero-hit terms stale via Edit tool with `<!-- stale: ... -->`, surfaces alias-creep, advises on husks.
- Phase 0.75 pre-scans recurrence artifacts BEFORE auto-Keep, so a recurrence-qualified entry with an unchanged module still reaches Phase 1; hardened entries get the gate-liveness check only.
- Phase 1 produces evidence per entry. For 3+ entries, parallel investigation subagents run.
- Phase 2 classifies; Replace candidates with insufficient evidence reclassify as mark-stale. Decision entries use the calibrated judging question and the supersede shape for Replace. Precedence: correctness > Consolidate > Harden.
- Phase 3 (interactive) groups Keeps / Updates for batched confirmation; presents Consolidate / Replace / Delete, Harden candidates (gate type + draft artifact + evidence + accept / different-gate-type / decline), and glossary alias-creep individually via blocking-question tool.
- Phase 4 executes via Write / `flowctl memory mark-stale` / `git rm`. Decision Replace = supersede (write new + edit old's `decision_status` + `superseded_by`; never `git rm`). Harden writes the artifact, verifies the gate fires, then `flowctl memory mark-hardened <id> --gate-ref "..."` — verification failure leaves the entry `active`; never `git rm`. Glossary stale = Edit comment after term heading.
- Phase 5 prints the report (memory section incl. `Hardened: N` with gate type / artifact path / gate-ref, glossary section + husk advisories); offers commit options based on git context.
- Phase 6 checks CLAUDE.md / AGENTS.md for `.flow/memory/` mention; offers minimal addition if missing.

In autofix mode (`/flow-next:audit mode:autofix`), Phase 3 is skipped, ambiguous entries are marked stale, glossary alias-creep surfaces as a recommendation only, Harden candidates and un-graduation proposals appear under Recommended without any artifact write or demotion, and the report is the sole deliverable.

If Phase 0 produces nothing (no categorized entries, only legacy) AND Phase 0.5 produces nothing (no glossary files), the skill exits cleanly with the legacy-skip count.
