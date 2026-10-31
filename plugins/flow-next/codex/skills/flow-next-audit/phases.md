# Memory audit — 6 outcomes lookup

For each entry, classify into exactly one outcome. Calibration below is specific to the `.flow/memory/` schema (track / category / module / tags / status frontmatter, body markdown). For the workflow phases that drive these decisions, see [workflow.md](workflow.md).

Persistence goes through `$FLOWCTL memory apply` ([workflow.md](workflow.md), Phase 4): where this file says `git rm` an entry, the plan marks it `remove: true`; never run `git rm` yourself.

Memory-entry body prose authored by the Update / Replace / Harden outcomes follows the artifact prose contract in [docs/prose.md](../../docs/flow-next/prose.md); proceed without it when the doc is absent.

| Outcome | Meaning | Default action |
|---------|---------|----------------|
| **Keep** | Still accurate and useful | No content edit; `stamp:true` in the apply plan; report reviewed-without-change |
| **Update** | Solution still correct, references drifted | Changed fields / body via the apply plan |
| **Consolidate** | Two entries overlap heavily, both correct | Merge unique content into canonical, remove subsumed via the apply plan |
| **Replace** | Old entry now misleading, successor exists / can be written | Write replacement entry, `git rm` old |
| **Delete** | Code gone AND problem domain gone | `remove:true` in the apply plan (preferred over stale-flag for truly obsolete) |
| **Harden** | Correct AND recurring AND mechanizable — the lesson should be a gate, not context | Write the gate artifact, verify it fires, then `flowctl memory mark-hardened` (file stays on disk) |

For **autofix mode** ambiguity: mark as stale via `flowctl memory mark-stale` instead of guessing.

The 6 outcomes apply to every categorized entry, including the `knowledge/decisions/` category. Decision entries reuse the same classifier with a tighter judging question and a different shape for `Replace` — see [references/decision-entries.md](references/decision-entries.md).

**Outcome precedence** when an entry qualifies for more than one — the [decision tree](#decision-tree-quick-reference) encodes this order:

1. **Correctness first (Replace / Delete).** A wrong or dead lesson is never graduated into a gate. Encoding bad guidance into lint/CI/instruction files makes it enforcement, and a wrong gate blocks every future run.
2. **Then Consolidate.** A `related_to` cluster is merged before the merged entry is considered for Harden — the cluster, not each member, is the Harden unit, so hardening members individually would produce duplicate gates for one lesson.
3. **Then Harden.** Only a correct, single, canonical entry is eligible.

Keep and Update are unaffected by this ordering: an entry that needs a reference fix and also qualifies for Harden gets the Update applied and then hardened in the same run (fix the lesson before retiring it).

**Intake filters** — for lessons arriving at the store (a new entry proposed during this audit, or judged as a fresh capture would be):

1. **A mechanizable lesson routes to a gate proposal, not a memory entry.** If a machine can check it deterministically, writing it as prose parks enforcement in the context window forever — propose the gate (the Harden target types in [references/harden-classify.md](references/harden-classify.md)) instead of banking the entry.
2. **Accept only lessons that route to something actually used in the transcript** — a file, command, or decision the session genuinely touched. A lesson abstracted past its evidence is speculation wearing a memory entry's clothes.
3. **A rule that existed but did not fire gets a retrieval fix, not a rewrite.** When the lesson was already in the store and the failure still happened, the defect is retrieval — description, placement, module/tags — not content; rewriting a correct rule that nobody surfaced just forks it.

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

- No content edit; `stamp:true` in the apply plan (see [workflow.md](workflow.md) §4.1).
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

**Retrieval-fix variant.** The entry is correct, recurrence-qualified (§0.75.1), fails the Harden mechanizability condition, and has a **nameable retrieval defect**: the lesson keeps being re-learned because the entry does not surface, not because it is wrong. Recurrence qualifies the entry for the question; it does not answer it. State the defect before editing — which of `title` / `tags` / `module` / `applies_when` / placement would miss the query this topic actually gets searched by. When the surface already carries them, there is **no retrieval fix** — the entry falls through to the ordinary reference-drift check and is Keep (reviewed without edits) absent drift of its own — not a cosmetic re-tag: §0.75.1's counters are all-history and never decrease, and the repair commit is itself substantive there, so an unconditional branch would re-fire on this entry at every later audit — repeated metadata churn and commits in autofix, forever. Repair the retrieval surface only — `title`, `tags`, `module`, `applies_when` (knowledge track), and placement (a `git mv` into the category the lesson belongs to, since category-scoped search and scope narrowing never reach a misfiled entry) — so the query the next agent will actually type matches. One field is off-limits: an entry whose **title is an upsert identity** — a deterministic title another skill re-derives and hands to `flowctl memory upsert`, which matches the stored title byte-for-byte within the track (the QA skill's `drift: <surface>/<feature-slug> <sub-feature-id>` `feature-map-drift` memos are the shipped case) — is never retitled. The rename stops matching, so the next observation files a sibling and the recurrence dedup the memo exists for is gone. Repair its other retrieval fields instead and say in the report line that the title was held as an upsert identity. Placement is unaffected: upsert matches on track and title, never on category. A placement move changes the entry id (it embeds the category): set the frontmatter `category` to the new bucket and re-point every `related_to` that named the old id, in the same edit, so path and metadata never disagree. Cite the recurrence artifacts in the report line as `retrieval fix: <fields>; <N> Update headings / <M> commits`. A body or solution edit *justified by the retrieval rationale* is a Replace in disguise: stop and reclassify. The "never the body" rule scopes what the retrieval defect licenses — it does not exempt the entry from the ordinary Update above: an entry that also carries plain reference drift (a renamed path in its body, a dead link, a stale snippet) still gets those repaired, on the ordinary Update's own evidence, in the same write. Both repairs land as one Update, reported as `retrieval fix: <fields>` plus the drift fixed.

**When NOT to use:**

- The body's recommended solution conflicts with current code — that's Replace.
- The fix in the body is now an anti-pattern — that's Replace.
- The architecture changed enough that the guidance is misleading — that's Replace.
- Two entries describe the same thing — that's Consolidate.
- Cosmetic-only changes (typo, prose polish) — skip; don't churn for no value.

**Action steps:**

1. Read the file (already loaded in Phase 1).
2. Mutate only the specific frontmatter fields that need updating. **Preserve all other fields** — `title`, `date`, `track`, `category`, plus any track-specific fields (`problem_type`, `symptoms`, `root_cause`, `resolution_type` for bug; `applies_when` for knowledge) and any unknown fields someone else added. The retrieval-fix variant above is the one exception, and only for the field it named as the defect: it may rewrite `title` (never an upsert identity), `tags`, `module`, `applies_when`, and — on a placement move — `category`, which is then set to the new bucket. Everything it did not name stays preserved.
3. Mutate the body for code-ref / link / snippet fixes.
4. Persist through the apply plan: changed fields under `set`, the revised `body` (see [workflow.md](workflow.md) §4.2).

**The Update boundary:**

> If you find yourself rewriting the solution section or changing what the entry recommends, stop — that is Replace, not Update.

**Edge cases:**

- Module field empty in frontmatter but body references a clear module → fill `module` as part of Update, with low-confidence flag.
- Multiple references in body — fix all of them; partial-fix updates are worse than no fix (next audit re-flags the same entry).
- Date field never changes on Update — `date` is the entry creation date, not last-modified. Use `last_updated` in optional fields if the schema includes it (see `MEMORY_OPTIONAL_FIELDS` in `flowctl.py`).

---

## Consolidate

**Meaning:** two or more entries overlap heavily and both / all are materially correct. Merge unique content into the canonical entry, then remove the subsumed ones.

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

**Action steps:** [workflow.md](workflow.md) §4.3.

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
3. **Re-point every `related_to` that names the old entry** to the new entry id, and remove the old id from the new entry's own `related_to` (`memory add` links a moderate-overlap match automatically). No `related_to` may name the deleted entry; git history records the relationship.
4. **Orchestrator `git rm`'s the old entry** after the subagent completes.

**Edge cases:**
- Replacement subagent's evidence comes back insufficient mid-write → abort, mark old entry stale, surface as a recommendation in the report.
- Successor pattern exists in code but is itself drifting (the new approach is being replaced by an even newer one) → this is rare; classify as Replace targeting the newest approach, with a short note in the body about the migration in progress.

---

## Delete

**Meaning:** the code referenced is gone AND the problem domain is gone. The entry no longer corresponds to any active concern in the codebase.

**When to use** (must meet ALL):

- The referenced files / modules are gone (a file search confirms).
- No search hits for class / function names mentioned in the body.
- No successor pattern visible in the same problem domain.
- No `related_to` cross-reference points at this entry from other active entries.

**When NOT to use:**

- Code is gone but problem domain persists (app still does auth, still processes payments, still handles migrations) → Replace, not Delete. The problem still matters; document the current approach.
- General advice is "still sound" but specific code is gone → Delete anyway. A learning about deleted features misleads readers into thinking those features still exist.
- Entry is fully redundant with a canonical entry → Consolidate (merge first if there's any unique content), not Delete.
- Borderline case → mark stale, not Delete.

**Auto-Delete criteria** (interactive too — bypass Phase 3 ask when ALL hold):

- Implementation gone (`module` path missing, no search hits).
- Problem domain gone (no successor pattern in the codebase).
- No active dependents (`related_to`).
- No conflicting newer entry suggesting a replacement.

When all four hold, Delete is unambiguous and runs without asking.

**Action steps:** an apply-plan entry with `remove:true` ([workflow.md](workflow.md) §4.5). No archive directory, no metadata flag. Git history preserves the file. Recovery: `git log --diff-filter=D -- .flow/memory/`.

**Edge cases:**

- Entry references files that exist but are tagged for deprecation → not Delete yet; the problem domain still exists. Mark stale with a deprecation note, or Replace if a successor pattern is documentable.
- Entry's body is general (e.g. "always validate inputs") with no code references → if the entry has no specific module / file ties, evaluate as a knowledge-track entry. If the principle still holds, Keep. If it's been superseded by a more specific knowledge entry, Consolidate.
- Entry is duplicated by a newer canonical entry that has fully absorbed its content → Consolidate (with no unique content to merge), then `git rm`. Functionally equivalent to Delete; the path through Consolidate makes the merge intent explicit in the report.

---

## Harden

**Meaning:** correct AND recurring AND mechanizable — graduate the lesson into a gate and demote the
entry to a pointer. Only for an entry or cluster §0.75.1 marked recurrence-qualified, or one whose evidence you judge
recurring below the numeric thresholds (state that evidence): read
[references/harden-classify.md](references/harden-classify.md) for the two conditions, gate targets,
duplication guard and edge cases. Harden never applies in autofix, and never `git rm` on Harden.

---

## Decision-entry calibration

Only when the audit set holds a `knowledge/decisions/` entry: read
[references/decision-entries.md](references/decision-entries.md) before judging it. Its core rule
holds everywhere: for a decision entry, Replace = supersede (write the successor, mark the old
`decision_status: superseded`, `superseded_by: <new-id>`), never `git rm` the old.

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
        gate live    → report as still-hardened; do NOT re-investigate
        gate gone    → propose `flowctl memory mark-fresh <id>` (un-graduate,
                       returns to active) with the evidence
        gate upgraded→ re-run mark-hardened with the new ref (idempotent)
  no  → continue

Is the entry under knowledge/decisions/?
  yes → use references/decision-entries.md
        (judging question = "does the constraint still hold?";
         Replace = supersede, not git rm; Harden is rare but legal — file stays on disk)
  no  → continue with the standard tree below

--- correctness first: a wrong lesson is never graduated into a gate ---

Is the entry's referenced code AND problem domain both gone?
  yes → Delete (auto-applicable when ALL auto-Delete criteria hold)
  no  → continue

Does the body's recommended solution conflict with current code?
  yes → enough evidence to write successor?
        yes → Replace (sequential subagent writes new; orchestrator deletes old)
        no  → mark stale (autofix) or ask user (interactive)
  no  → continue

--- then Consolidate: the cluster, not each member, is the Harden unit ---

Does another entry in the same module/category overlap heavily?
  yes → Consolidate (canonical = newer/broader; subsumed → merged + git rm)
        then re-enter this tree ONCE with the merged entry
  no  → continue

--- then Harden: only a correct, single, canonical entry is eligible ---

Recurrence signal? (>= 2 `## Update` headings OR >= 4 commits on the entry file;
a related_to cluster >= 3 only corroborates — it proposes nothing on its own)
  yes → is the lesson mechanizable (a deterministic check a gate can run)?
        yes → duplication guard: does an ACTIVE gate already enforce the class?
              active match   → propose pointer-demotion citing that gate, no new artifact
              inactive match → broken gate: entry stays active, report the finding
              no match       → Harden (pick gate type a→b→c, draft artifact,
                               ask, write, VERIFY the gate fires, then mark-hardened)
        no  → nameable retrieval defect in title / tags / module / applies_when /
              placement (the surface would miss the query this topic gets searched by)?
              yes → Update, retrieval-fix variant (repair the surface, never the
                    body — see §Update), then continue to the drift check below
                    and fold any ordinary reference repairs into the SAME Update
              no  → continue (recurrence alone never re-fires a repaired entry)
  no  → continue

Are there reference drifts (paths, modules, links, snippets)?
  yes → Update (apply plan; preserve unknown frontmatter) — one Update per entry,
        carrying the retrieval-surface repair too if one was named above
  no  → Keep (`stamp:true` only; report under "Reviewed without edits"), unless a retrieval
        fix was named above — then it is that Update alone
```

An entry needing both an Update and a Harden gets the Update applied first — fix the lesson before retiring it — then hardened in the same run.

In autofix mode, replace any "ask user" branch with mark-stale, and **Harden never applies**: candidates (and un-graduation proposals) are reported under Recommended only — no artifact write, no demotion.

For glossary terms (separate from memory entries — see [references/glossary-scan.md](references/glossary-scan.md)): the tree is `code-hit? → Keep`; `no code-hit AND no alias-hit? → mark stale via Edit tool`; `alias hit in code? → Phase 3 question (interactive) or stale-flag note (autofix)`.
