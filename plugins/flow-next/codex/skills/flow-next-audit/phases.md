# Memory audit — 6 outcomes lookup

For each entry, classify into exactly one outcome. Calibration below is specific to the `.flow/memory/` schema (track / category / module / tags / status frontmatter, body markdown). For the workflow phases that drive these decisions, see [workflow.md](workflow.md).

| Outcome | Meaning | Default action |
|---------|---------|----------------|
| **Keep** | Still accurate and useful | No edit; report reviewed-without-change |
| **Update** | Solution still correct, references drifted | Agent edits in place via Write tool |
| **Consolidate** | Two entries overlap heavily, both correct | Merge unique content into canonical, `git rm` subsumed |
| **Replace** | Old entry now misleading, successor exists / can be written | Write replacement entry, `git rm` old |
| **Delete** | Code gone AND problem domain gone | `git rm` (preferred over stale-flag for truly obsolete) |
| **Harden** | Correct AND recurring AND mechanizable — the lesson should be a gate, not context | Write the gate artifact, verify it fires, then `flowctl memory mark-hardened` (file stays on disk) |

For **autofix mode** ambiguity: mark as stale via `flowctl memory mark-stale` instead of guessing.

The 6 outcomes apply to every categorized entry, including the `knowledge/decisions/` category (fn-38 schema extension). Decision entries reuse the same classifier with a tighter judging question and a different shape for `Replace` — see the [Decision-entry calibration](#decision-entry-calibration) section below.

**Outcome precedence** when an entry qualifies for more than one — the [decision tree](#decision-tree-quick-reference) encodes this order:

1. **Correctness first (Replace / Delete).** A wrong or dead lesson is never graduated into a gate. Encoding bad guidance into lint/CI/instruction files makes it enforcement, and a wrong gate blocks every future run.
2. **Then Consolidate.** A `related_to` cluster is merged before the merged entry is considered for Harden — the cluster, not each member, is the Harden unit, so hardening members individually would produce duplicate gates for one lesson.
3. **Then Harden.** Only a correct, single, canonical entry is eligible.

Keep and Update are unaffected by this ordering: an entry that needs a reference fix and also qualifies for Harden gets the Update applied and then hardened in the same run (fix the lesson before retiring it).

---

## Keep

**Meaning:** the entry is still accurate AND still useful.

**When to use:**

- Module / referenced files still exist.
- Body's recommended solution still matches how the code works today.
- Code snippets in body still reflect current implementation.
- `related_to` cross-references still resolve.
- Problem domain still exists in the codebase.

**When NOT to use:**

- Anything looks stale — pick Update / Consolidate / Replace / Delete.
- "It might be useful someday" — that's how the store accumulates zombies. If there's no current value, classify as Delete.

**Action steps:**

- No file edit.
- Report under "Reviewed without edits" subsection (see [workflow.md](workflow.md) §5.1).

**Edge cases:**

- An entry with one broken `related_to` link but otherwise accurate → Update (fix the cross-reference), not Keep.
- An entry whose `module` field is outdated but body still describes current code accurately → Update (fix `module`), not Keep.
- An entry that references an internal helper that was inlined — solution intent still applies — Update (fix the reference), not Keep.

---

## Update

**Meaning:** the core solution is still correct, but references have drifted (paths, modules, code snippets, links).

**When to use:**

- File renamed → fix the `module` field and any body references.
- Function / class moved → fix the body references.
- Tags drifted from current convention → tighten the `tags` array.
- `related_to` points at a stale entry that itself was updated to a new id → re-point.
- Code snippet in body uses an outdated import path → fix the snippet.

**When NOT to use:**

- The body's recommended solution conflicts with current code — that's Replace.
- The fix in the body is now an anti-pattern — that's Replace.
- The architecture changed enough that the guidance is misleading — that's Replace.
- Two entries describe the same thing — that's Consolidate.
- Cosmetic-only changes (typo, prose polish) — skip; don't churn for no value.

**Action steps:**

1. Read the file (already loaded in Phase 1).
2. Mutate only the specific frontmatter fields that need updating. **Preserve all other fields** — `title`, `date`, `track`, `category`, plus any track-specific fields (`problem_type`, `symptoms`, `root_cause`, `resolution_type` for bug; `applies_when` for knowledge) and any unknown fields someone else added.
3. Mutate the body for code-ref / link / snippet fixes.
4. Write the file back via the Write tool.
5. **Round-trip safety:** if frontmatter has quirky YAML (anchors, nested structures, multi-line values) the agent isn't confident parsing, prefer `flowctl memory mark-stale` for stale-flagging — that helper handles round-trip correctly via existing `write_memory_entry`.

**The Update boundary:**

> If you find yourself rewriting the solution section or changing what the entry recommends, stop — that is Replace, not Update.

**Edge cases:**

- Module field empty in frontmatter but body references a clear module → fill `module` as part of Update, with low-confidence flag.
- Multiple references in body — fix all of them; partial-fix updates are worse than no fix (next audit re-flags the same entry).
- Date field never changes on Update — `date` is the entry creation date, not last-modified. Use `last_updated` in optional fields if the schema includes it (see `MEMORY_OPTIONAL_FIELDS` in `flowctl.py`).

---

## Consolidate

**Meaning:** two or more entries overlap heavily and both / all are materially correct. Merge unique content into the canonical entry, then `git rm` the subsumed ones.

**When to use** (apply Phase 1.75 cross-doc analysis):

- Two entries describe the same problem and recommend the same (or compatible) solution.
- One entry is a narrow precursor; a newer entry covers the same ground more broadly.
- Unique content from the subsumed entry can fit naturally as a section / paragraph in the canonical entry.
- Keeping both creates drift risk without meaningful retrieval benefit.

**When NOT to use** (Retrieval-Value Test from [workflow.md](workflow.md) §1.75):

- The entries cover genuinely different sub-problems someone would search for independently.
- Merging would create an unwieldy entry harder to navigate than two focused ones.
- The subsumed entry has truly distinct content with independent value (edge case examples, alternative debugging paths).

**Consolidate vs Delete:**

- Subsumed entry has unique content worth preserving → Consolidate (merge first, then delete).
- Subsumed entry adds nothing the canonical doesn't already say → skip straight to Delete.

**Action steps:**

1. **Confirm canonical entry** — most recent date, broadest module scope, highest-confidence Phase 1 recommendation, cleanest body.
2. **Extract unique content** from subsumed entries — diff against canonical body. Edge cases, alternative approaches, extra prevention rules.
3. **Merge into canonical:**
 - Integrate unique content where it logically belongs (don't blindly append).
 - Combine `tags` arrays (dedupe).
 - Preserve canonical's `module`, `track`, `category` — those are the canonical key.
 - Optional: append `related_to: [<subsumed_id>, ...]` for traceability (git history also captures this).
4. **Update other entries' `related_to`** — if any other entries cross-reference the subsumed entries, re-point to canonical.
5. **`git rm` subsumed entries.** No archival, no redirect metadata. Git history preserves them; recovery via `git log --diff-filter=D -- .flow/memory/`.

**Edge cases:**

- 3+ overlapping entries: process pairwise. Consolidate the two most overlapping first, then evaluate the merged result against the next.
- Mixed track / category clusters (e.g. one is `bug/runtime-errors`, another is `knowledge/conventions` — both about the same module) → these usually do NOT consolidate. Different tracks serve different retrieval intents. Keep separate; cross-reference via `related_to`.
- One entry has 5 tags, the other has 3, with overlap of 2 → merged `tags` array is the dedup'd union. Preserve specificity over generality.

**Structural splits (reverse Consolidate):**

If one entry has grown unwieldy and covers multiple distinct problems that would benefit from separate retrieval, split it. Only when sub-topics are genuinely independent.

---

## Replace

**Meaning:** the entry's core guidance is now misleading — the recommended fix changed materially, the root cause / architecture shifted, or the preferred pattern is different. The problem domain still matters; the documented approach doesn't.

**When to use:**

- Body recommends approach X; current code uses approach Y, and Y is the new preferred pattern.
- Architecture changed; old solution conflicts with current shape.
- Bug entry: the bug is still possible, but the fix changed (e.g. switched libraries, restructured the affected module).
- Knowledge entry: the convention / pattern changed; the old guidance would mislead someone reading it today.

**When NOT to use:**

- References drifted but solution still applies → Update.
- Code is gone AND problem domain is gone → Delete.
- The entry is correct, just overlaps with a newer canonical → Consolidate.

**Evidence sufficiency check** (the gate):

By the time you identify a Replace candidate, Phase 1 investigation gathered evidence: the old recommendation, what current code does, where drift occurred. Assess whether this is enough to write a trustworthy successor:

- **Sufficient evidence** — you understand both old recommendation AND current approach. New file locations, current pattern, why old guidance misleads. → proceed to Replace flow.
- **Insufficient evidence** — drift is so fundamental you can't confidently document the current approach. Entire subsystem replaced; new architecture too complex to summarize from a file scan. → mark stale instead:
 - `flowctl memory mark-stale <id> --reason "<what was found, what's missing>" --audited-by "/flow-next:audit"`
 - Report what evidence was found and what's missing.
 - Recommend the user run a domain-specific solve afterward to capture fresh context.

In autofix mode, "insufficient evidence" always routes to mark-stale, never a half-baked Replace.

**Action steps (sufficient evidence):**

Process Replace candidates **one at a time, sequentially.** Each replacement may need significant code investigation; parallel runs risk orchestrator context exhaustion.

1. **Spawn a single subagent** (sequential) to write the replacement. Pass:
 - Old entry's full content.
 - Investigation evidence summary (what changed, current pattern, why old misleads).
 - Target track + category. Same as old unless the category itself drifted (e.g. a `bug/integration` entry whose problem domain morphed into a `knowledge/architecture-patterns` issue — agent decides).
 - Memory schema reference (the `MEMORY_REQUIRED_FIELDS` / `MEMORY_BUG_FIELDS` / `MEMORY_KNOWLEDGE_FIELDS` / `MEMORY_OPTIONAL_FIELDS` constants in `flowctl.py`):
 - Required: `title`, `date`, `track`, `category`.
 - Track-specific bug: `problem_type`, `symptoms`, `root_cause`, `resolution_type`.
 - Track-specific knowledge: `applies_when`.
 - Optional: `module`, `tags`, `related_to`, `status`.
2. **Subagent writes the new entry** via Write tool OR `flowctl memory add --track <t> --category <c> --title "..." --module <m> --tags "a,b" --body-file <path>`. flowctl `add` enforces schema validation; direct Write requires the subagent to emit valid frontmatter.
3. **Optional traceability** — new entry's frontmatter may include `related_to: [<old-id>]`. Git history also captures the relationship.
4. **Orchestrator `git rm`'s the old entry** after the subagent completes.

**Edge cases:**

- Old entry has dependents (`related_to` from other entries) → update their `related_to` to point at the new entry id.
- Replacement subagent's evidence comes back insufficient mid-write → abort, mark old entry stale, surface as a recommendation in the report.
- Successor pattern exists in code but is itself drifting (the new approach is being replaced by an even newer one) → this is rare; classify as Replace targeting the newest approach, with a short note in the body about the migration in progress.

---

## Delete

**Meaning:** the code referenced is gone AND the problem domain is gone. The entry no longer corresponds to any active concern in the codebase.

**When to use** (must meet ALL):

- The referenced files / modules are gone (Glob confirms).
- No Grep hits for class / function names mentioned in the body.
- No successor pattern visible in the same problem domain.
- No `related_to` cross-reference points at this entry from other active entries.

**When NOT to use:**

- Code is gone but problem domain persists (app still does auth, still processes payments, still handles migrations) → Replace, not Delete. The problem still matters; document the current approach.
- General advice is "still sound" but specific code is gone → Delete anyway. A learning about deleted features misleads readers into thinking those features still exist.
- Entry is fully redundant with a canonical entry → Consolidate (merge first if there's any unique content), not Delete.
- Borderline case → mark stale, not Delete.

**Auto-Delete criteria** (interactive too — bypass Phase 3 ask when ALL hold):

- Implementation gone (`module` path missing, no Grep hits).
- Problem domain gone (no successor pattern in the codebase).
- No active dependents (`related_to`).
- No conflicting newer entry suggesting a replacement.

When all four hold, Delete is unambiguous and runs without asking.

**Action steps:**

```bash
git rm "$REPO_ROOT/<entry-path>"
```

That's it. No archive directory, no metadata flag. Git history preserves the file. Recovery: `git log --diff-filter=D -- .flow/memory/`.

**Edge cases:**

- Entry references files that exist but are tagged for deprecation → not Delete yet; the problem domain still exists. Mark stale with a deprecation note, or Replace if a successor pattern is documentable.
- Entry's body is general (e.g. "always validate inputs") with no code references → if the entry has no specific module / file ties, evaluate as a knowledge-track entry. If the principle still holds, Keep. If it's been superseded by a more specific knowledge entry, Consolidate.
- Entry is duplicated by a newer canonical entry that has fully absorbed its content → Consolidate (with no unique content to merge), then `git rm`. Functionally equivalent to Delete; the path through Consolidate makes the merge intent explicit in the report.

---

## Harden

**Meaning:** the entry is correct, keeps getting re-learned, and states a rule a machine can check. Graduate it into an enforced gate (lint rule / CI step / instruction-file rule) and demote the entry to a pointer at that gate. The lesson stops riding the context window on every run and starts firing automatically — for every agent and every human, in every harness.

An entry that is re-injected each run and re-taught each time is the anti-pattern: the agent re-fixes the same class instead of the class being impossible. Harden closes that loop.

**Two conditions, both required (AND):**

**(1) Recurrence signal.** There is **no read-side usage telemetry** in flow-next — `memory-scout` retrieval and worker re-anchor reads leave zero trace on the entry, and nothing records "this entry fired during a run." Recurrence is therefore an inference over **write-side artifacts** plus LLM judgment, never a counter read. The artifacts, per entry:

```bash
grep -c '^## Update ' <entry-file> # reinforcement writes (memory add --update)
# substantive write history — see workflow.md §0.75.1 for the exact command; it filters out
# commits whose diff on the entry touches only audit bookkeeping (last_audited, audit_notes,
# status, stale_reason, stale_date, hardened_into)
# frontmatter: related_to length, last_updated
```

An entry (or cluster) becomes a **candidate** when ANY primary signal fires:

- (i) **`>= 2` `## Update` headings** on the entry — the lesson was explicitly re-taught at least twice.
- (iii) **`>= 4` substantive commits** touching the entry file — sustained write churn on one lesson. **Audit-stamp commits do not count**: a commit whose diff on the entry changes only `last_audited` / `audit_notes` / `status` / `stale_reason` / `stale_date` / `hardened_into` is the audit's own bookkeeping, not a re-teaching. Counting them would let three routine sweeps in a repo that commits its audits push every entry over the threshold — recurrence would then track audit diligence, not recurring pain.

`related_to` cluster size is a **corroborating signal only**: a cluster of `>= 3` raises a candidate ONLY when it co-occurs with at least one `## Update` heading somewhere in the cluster, or with signal (iii) on any member. **On its own it proposes nothing.**

> **Calibration evidence (this repo's store, 71 entries, measured 2026-07-24).** Signal (i) matched 3 entries (4%); signal (iii) matched ~1 in 20 sampled (~5%) — measured on a store whose commits were all substantive, so the bookkeeping filter leaves that rate unchanged here and only holds it steady as audits accumulate; a standalone `related_to >= 3` trigger would have matched 20 entries (**28%**). `related_to` is auto-populated by overlap scoring on every `memory add`, so cluster size measures topic collision, not re-teaching — left standalone it would flag more than a quarter of the store on the first run and train the user to decline Harden reflexively. Signals (i) and (iii) are selective and match the recurring-pain intuition, so they keep their values.

Thresholds gate **proposing** only; the human gates **applying**. They are overridable by judgment in either direction — state the evidence when you override (e.g. a single-`## Update` entry that names a rule the linter already almost covers is worth proposing; four commits that were all typo fixes are not recurrence).

**(2) Mechanizability.** The lesson must be expressible as a deterministic check a gate can run — always LLM-judged, never inferred from the counts. "Never use naive `datetime.now()`" is mechanizable. "Prefer composition over inheritance when the hierarchy gets awkward" is not.

**When to use:**

- Both conditions hold: a recurrence signal fires AND the lesson is a deterministic, checkable rule.
- The rule can land in a gate surface that **already exists** in this repo (see Gate targets below).
- No existing, active gate already enforces the class (see Duplication guard).

**When NOT to use:**

- The lesson is wrong, misleading, or its code is gone → Replace / Delete win outright (precedence). Never graduate a wrong lesson.
- The entry is one of several overlapping entries → Consolidate first; the merged entry is the Harden unit.
- One-off lesson, no recurrence signal → Keep.
- Judgment-only lesson ("prefer X style when ambiguous", "escalate when the review disagrees") → Keep. A gate that cannot decide mechanically becomes a false-positive generator.
- The repo has no surface to host the gate — see the degradation rule below; the instruction file is the universal floor, and if even that does not exist, Keep.
- **Autofix mode.** Harden never auto-applies. Candidates are reported under Recommended only — no artifact write, no demotion. Gate surfaces are shared repo infrastructure; an autonomous sweep must not edit lint config, CI, or CLAUDE.md unattended.

**Gate targets — cheapest-fitting first, discovered from repo files, never assumed and never scaffolded:**

- **(a) Lint rule** — extend the repo's existing linter config (ruff, biome, eslint, … — discovered by reading the repo, not assumed from the language). No linter configured → unavailable, fall through.
- **(b) CI step** — a check in the repo's existing CI workflow (e.g. under `.github/workflows/`). No CI → unavailable, fall through.
- **(c) Instruction-file rule** — a one-to-two-line rule appended to the **substantive** CLAUDE.md / AGENTS.md (the one that is not just an `@`-include shim — the same "which file is real" discovery as [workflow.md](workflow.md) Phase 6). This is the **universal floor** and the degradation target for review-shaped lessons, since a first-class review-checklist gate type is deliberately out of v1 (no canonical checklist artifact exists to write into).

**Never scaffold infrastructure to host a gate.** Do not create a linter setup, a CI pipeline, or a config file that does not already exist. The gate lands in what the repo already has, or it degrades to (c), or the entry stays Keep.

**Duplication guard (run BEFORE proposing):** grep the candidate gate surfaces (linter config, CI workflows, instruction files) for a rule already covering the class.

- **Matched AND active** (confirmed by the same liveness check as the verification step below) → the class is already enforced. Propose **pointer-demotion only**: no new artifact, `mark-hardened` citing the *existing* gate as `--gate-ref`.
- **Matched but inactive** (commented out, sitting in an `ignore` list, in a config the tool does not read, in a disabled or unreferenced CI job) → this is **not** a duplicate, it is a broken gate. The entry **stays `active`**, nothing is demoted, and the finding is reported so a human can fix the gate.
- **No match** → proceed with a new artifact.

A textual hit is never sufficient evidence of enforcement.

**Action steps:**

1. **Gather the recurrence artifacts** (the commands above) — done in [workflow.md](workflow.md) Phase 1, and for Harden specifically *before* the Phase 0.75 auto-Keep decision.
2. **Judge mechanizability.** Not mechanizable → Keep, stop.
3. **Run the duplication guard.** Active match → pointer-demotion path (skip to step 6 with the existing gate's ref). Inactive match → report the broken gate, entry stays `active`, stop.
4. **Pick the gate type** (a) → (b) → (c), cheapest fitting first, and **draft the artifact** — the concrete config/YAML/prose line for THIS repo. The draft is shown in the Phase 3 ask before anything is written.
5. **On acceptance, write the artifact**, then **verify the gate actually fires** (below). Verification failure → entry stays `active`, `mark-hardened` is NOT called, report a failed graduation with the reason.
6. **Demote** — only after verification passes:

 ```bash
 "$FLOWCTL" memory mark-hardened "$ENTRY_ID" \
 --gate-ref "<path>#<rule-id> -- <note>" \
 --audited-by "/flow-next:audit"
 ```

 This sets `status: hardened`, stores `hardened_into` verbatim, clears the stale-only fields, and stamps `last_audited` (a UTC date — a same-day re-mark is observably a no-op on that field). **The entry file stays on disk with its body intact** — it becomes a pointer, so provenance survives and "why does this lint rule exist?" stays answerable forever. **Never `git rm` on Harden**, on any track.

**Gate verification before demotion — the load-bearing step.** Writing config is not the same as enforcing a rule. A gate that does not fire is strictly worse than no gate: it retires the only working copy of the lesson while enforcing nothing. Verify by gate type:

- **lint** — run the linter and confirm the new rule is active in the **resolved** config: not merely present as text in a file the tool does not read, and not neutralized by a later `ignore` / disable entry.
- **CI** — confirm the step parses and sits in a workflow AND a job that actually run on the relevant trigger — not a disabled, unreferenced, or manual-only one.
- **instruction file** — confirm the rule landed in the **substantive** file the agents actually read, not an `@`-including stub.

**`--gate-ref` composition.** The audit skill owns the format; flowctl stores it verbatim and validates nothing but non-emptiness (parsing it there would be judgment leaking into plumbing). The format is:

```
<path>#<rule-id> -- <note>
```

`<path>` is repo-relative. `<rule-id>` must be a token a later `grep` can find **in that file** — that is what makes the gate-liveness check on the next audit run possible; a prose description would give the next audit nothing to look at. `<note>` is a short human gloss. One example per gate type:

- lint: `pyproject.toml#tool.ruff.select:DTZ -- bans naive datetimes`
- CI: `.github/workflows/ci.yml#jobs.lint.steps[name=ruff] -- runs the DTZ gate`
- instruction file: `CLAUDE.md#timestamps-utc -- always stamp UTC ISO-8601`

**Already-hardened entries on later runs (gate-liveness check).** A hardened entry is never dropped silently and never fully re-investigated. Grep `<path>` for `<rule-id>` from its `hardened_into`, and apply the same activeness check as verification:

- **Gate present and active** → report as still-hardened. Done; no re-investigation.
- **Gate gone or now inactive** → the lesson is stranded outside the context window with no enforcement. Propose un-graduation: `flowctl memory mark-fresh <id>` (returns the entry to `active` and drops `hardened_into`), with the evidence — which surface was checked and what was missing. Interactive asks; autofix reports it under Recommended.
- **Gate upgraded** (e.g. an instruction-file rule promoted to a lint rule) → re-run `mark-hardened` with the new ref. It is idempotent and replaces `hardened_into`.

**Edge cases:**

- **Cluster candidates** — the cluster, not each member, is the Harden unit. Consolidate first (precedence), then evaluate the merged entry once. Never write one gate per member.
- **Decision-track entries** (`knowledge/decisions/`) — `mark-hardened` keeps the file on disk, consistent with "decision history stays on disk", and the supersession fields (`decision_status`, `superseded_by`, `alternatives_considered`) are preserved alongside the new status. Expect Harden to be **rare** here: most decisions are judgment records, not mechanizable checks.
- **Stale entries** — `stale → hardened` is legal. A lesson can be stale as written and still name a real, mechanizable class; `mark-hardened` clears `stale_reason` / `stale_date` as part of the flip. Do not force a `mark-fresh` round trip first.
- **Non-code repos** (docs sites, an Obsidian vault) — targets (a)/(b) are simply unavailable; (c) is the floor.
- **First post-ship run** — recurrence signals are derived retroactively, so the first ordinary audit after this ships may surface several candidates at once. That is intended: the thresholds above are what keeps the volume sane, and there is no first-run suppression or rate limit.
- **Legacy flat files** — skipped as always; migrate first.

---

## Decision-entry calibration

Entries under `knowledge/decisions/` (fn-38 schema) document forward-looking choices: the project picked approach X, considered Y and Z, and committed to a constraint. The 6 outcomes still apply, but the per-entry judging question changes — and `Replace` means **supersede**, not rewrite-in-place.

### Per-entry judging question

For non-decision entries, Phase 1 asks "is this still relevant?". For decision entries, ask:

> **Does the constraint that motivated this decision still hold?**

The constraint is whatever made the decision hard-to-reverse, surprising-without-context, and a real trade-off when it was made. If the constraint is still in force, the decision is still active. If the constraint has dissolved (the trade-off no longer exists, the surprising context is now the obvious default, the codebase changed shape so reversal is now cheap), the decision is a candidate for supersession.

### Decision-specific frontmatter

Decision entries may carry these optional fields (see `MEMORY_DECISION_FIELDS` in `flowctl.py`):

- `decision_status`: one of `proposed`, `accepted`, `superseded` (`MEMORY_DECISION_STATUSES`)
- `superseded_by`: id of the successor entry that replaced this one
- `alternatives_considered`: list of options that were rejected when the decision was made

When auditing, treat `decision_status: superseded` as already-handled — the entry is historical record. Audit the `superseded_by` target instead. If `superseded_by` points at a missing entry, that's an Update (broken cross-reference) on this entry.

### Outcome calibration for decisions

| Outcome | Meaning for a decision entry | Action |
|---------|------------------------------|--------|
| **Keep** | Constraint still holds; rejected alternatives are still rejected for the same reasons | No edit |
| **Update** | Constraint holds; only references / `alternatives_considered` text / cross-refs drifted | Edit in place; `decision_status` unchanged |
| **Consolidate** | Two decision entries cover the same choice (rare — usually means a rushed double-write) | Merge into canonical, `git rm` subsumed |
| **Replace** | Constraint no longer holds; a different choice is now in force | **Supersede** — see flow below |
| **Delete** | The entire problem area is gone (the system that needed the decision was removed) | `git rm` (prefer Replace + supersede when problem domain still exists) |
| **Harden** | Rare — the decision states a constraint a machine can check, and it keeps being re-taught | Write the gate, verify it fires, `flowctl memory mark-hardened`; file stays on disk, supersession fields preserved |

**Harden is expected to be rare on decision entries.** Most decisions are judgment records — "we chose X over Y because of trade-off Z" — and a trade-off rationale is not a deterministic check. The calibrated judging question above ("does the constraint still hold?") stays primary; only reach for Harden when the decision's constraint is itself mechanically checkable (e.g. "all timestamps are UTC ISO-8601" rather than "we prefer a monorepo"). Because `mark-hardened` never removes the file, hardening a decision does not conflict with the supersede-not-delete rule.

### Replace = supersede

For non-decision entries, `Replace` means write a successor and `git rm` the old. For decision entries, the old entry stays — it's part of the history of why the project arrived where it is. Replace becomes a two-step supersession:

1. **Write the new decision entry** — a fresh `knowledge/decisions/<slug>-<date>.md` describing the current choice, what changed in the constraint, and why the prior decision no longer applies. Optionally include `alternatives_considered` listing both the original alternatives and the prior decision itself (now also rejected). Include `related_to: [<old-id>]` for traceability.
2. **Mark the old entry superseded** — Edit the old entry's frontmatter to set `decision_status: superseded` and `superseded_by: <new-entry-id>`. Body untouched. Do **not** `git rm` — the historical record stays on disk.

When autofix evidence is insufficient to write the successor decision (the constraint clearly dissolved but the new approach is too unstable to commit to), mark the old entry stale via `flowctl memory mark-stale` instead of half-shipping a supersession. The user (or a follow-up audit) can revisit when the new approach has settled.

### Edge cases

- A decision whose `decision_status` is `proposed` but never reached `accepted` (the project never committed) → if no code reflects the proposal, classify Delete; if partial implementation exists, mark stale and surface in the report.
- A decision that references a constraint visible only in external context (a contract, a partner integration, a regulatory rule) → audit cannot verify the constraint from code alone. Skip with a "cannot mechanically verify" note in the report; do not auto-Delete.
- A decision pointing at `superseded_by: <id>` where the successor itself is now superseded → walk the chain; the audit target is the head of the chain.

---

## Glossary scan (parallel to memory audit)

Glossary terms are not memory entries — they live in `GLOSSARY.md` files at the repo root and (optionally) under subdirectories. The audit walks them in [Phase 0.5](workflow.md) of the workflow. The 6-outcomes table doesn't apply directly; the per-term decisions are simpler:

| Outcome | Meaning for a glossary term | Action |
|---------|-----------------------------|--------|
| **Keep** | Term has hits in tracked code (case-insensitive whole-word match) | No edit |
| **Mark stale** | Zero hits for the term AND zero hits for any `_Avoid_` alias | Edit tool: append `<!-- stale: <reason> -->` HTML comment after the term heading |
| **Alias-creep** | An `_Avoid_` alias has hits in code | Phase 3 question (interactive) or stale-flag note (autofix) — propose renaming code uses to the canonical term, or moving the alias out of `_Avoid_` |

There is no `flowctl glossary mark-stale` subcommand. Stale-marking is an Edit-tool operation only. The agent must **never delete** the term entry on stale-detection — deletion is the operator's call, surfaced as a recommendation in the report.

### Husk awareness

A glossary file with `count: 0` from `flowctl glossary list --json` is a husk — `# Glossary` H1 with no terms after the last term was removed. Husks have no terms to audit; skip the walk for that file and surface a single advisory in Phase 5:

```
GLOSSARY.md at <path> is an empty husk (no terms defined).
Remove the file manually if it's no longer needed; flow-next keeps it as
project state per fn-38 R18.
```

The audit never deletes the file. Removing it is a project decision, not a memory-audit decision.

---

## Mark stale (autofix ambiguous + Replace-insufficient)

**Not** one of the 6 outcomes — it's the autofix-mode escape hatch and the Replace-insufficient-evidence fallback. Surface in the report under "Marked stale" with the reason.

**When to use:**

- **Autofix mode, ambiguous classification** — Update vs Replace vs Consolidate is genuinely unclear and there's no user to ask.
- **Replace candidate, insufficient evidence** — drift is real but successor evidence is too thin to write a trustworthy replacement.

**Action:**

```bash
"$FLOWCTL" memory mark-stale "$ENTRY_ID" \
 --reason "<one-line ambiguity description>" \
 --audited-by "/flow-next:audit"
```

The helper sets `status: stale`, stamps `last_audited` (today's date), records `audit_notes` from `--reason`. Atomic — preserves unknown frontmatter fields.

**Effect on search:**

`flowctl memory search` (without `--status`) defaults to `--status active` — stale entries don't surface in default scout queries. They're still readable via `--status stale` or `--status all`. The user (or a future audit) can revisit later.

**Idempotency:**

Re-mark-stale on an already-stale entry updates `last_audited` + `audit_notes`. No-op if you really want; the helper handles both cases. The audit reports it under "Already stale (re-audited)" rather than "Marked stale" so the count reflects new flags accurately.

---

## Decision tree (quick reference)

The tree is ordered by the precedence rule at the top of this file: **correctness (Replace / Delete) > Consolidate > Harden**. Correctness runs first because a wrong lesson must never become an enforced gate; Consolidate runs before Harden because the cluster, not each member, is the Harden unit.

```
Is the entry already status: hardened?
 yes → gate-liveness check only (grep <path> for <rule-id> from hardened_into,
 confirm the rule is ACTIVE — not commented out / ignored / in a dead job)
 gate live → report as still-hardened; do NOT re-investigate
 gate gone → propose `flowctl memory mark-fresh <id>` (un-graduate,
 returns to active) with the evidence
 gate upgraded→ re-run mark-hardened with the new ref (idempotent)
 no → continue

Is the entry under knowledge/decisions/?
 yes → use the Decision-entry calibration block above
 (judging question = "does the constraint still hold?";
 Replace = supersede, not git rm; Harden is rare but legal — file stays on disk)
 no → continue with the standard tree below

--- correctness first: a wrong lesson is never graduated into a gate ---

Is the entry's referenced code AND problem domain both gone?
 yes → Delete (auto-applicable when ALL auto-Delete criteria hold)
 no → continue

Does the body's recommended solution conflict with current code?
 yes → enough evidence to write successor?
 yes → Replace (sequential subagent writes new; orchestrator deletes old)
 no → mark stale (autofix) or ask user (interactive)
 no → continue

--- then Consolidate: the cluster, not each member, is the Harden unit ---

Does another entry in the same module/category overlap heavily?
 yes → Consolidate (canonical = newer/broader; subsumed → merged + git rm)
 then re-enter this tree ONCE with the merged entry
 no → continue

--- then Harden: only a correct, single, canonical entry is eligible ---

Recurrence signal? (>= 2 `## Update` headings OR >= 4 commits on the entry file;
a related_to cluster >= 3 only corroborates — it proposes nothing on its own)
 yes → is the lesson mechanizable (a deterministic check a gate can run)?
 yes → duplication guard: does an ACTIVE gate already enforce the class?
 active match → propose pointer-demotion citing that gate, no new artifact
 inactive match → broken gate: entry stays active, report the finding
 no match → Harden (pick gate type a→b→c, draft artifact,
 ask, write, VERIFY the gate fires, then mark-hardened)
 no → Keep (judgment-only lessons stay context, not gates)
 no → continue

Are there reference drifts (paths, modules, links, snippets)?
 yes → Update (write tool; preserve unknown frontmatter)
 no → Keep (no edit; report under "Reviewed without edits")
```

An entry needing both an Update and a Harden gets the Update applied first — fix the lesson before retiring it — then hardened in the same run.

In autofix mode, replace any "ask user" branch with mark-stale, and **Harden never applies**: candidates (and un-graduation proposals) are reported under Recommended only — no artifact write, no demotion.

For glossary terms (separate from memory entries — see [Glossary scan](#glossary-scan-parallel-to-memory-audit) above): the tree is `code-hit? → Keep`; `no code-hit AND no alias-hit? → mark stale via Edit tool`; `alias hit in code? → Phase 3 question (interactive) or stale-flag note (autofix)`.
