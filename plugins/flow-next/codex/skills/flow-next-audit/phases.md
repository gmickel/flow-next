# Memory audit — 5 outcomes lookup

For each entry, classify into exactly one outcome. Calibration below is specific to the `.flow/memory/` schema (track / category / module / tags / status frontmatter, body markdown). For the workflow phases that drive these decisions, see [workflow.md](workflow.md).

| Outcome | Meaning | Default action |
|---------|---------|----------------|
| **Keep** | Still accurate and useful | No edit; report reviewed-without-change |
| **Update** | Solution still correct, references drifted | Agent edits in place via Write tool |
| **Consolidate** | Two entries overlap heavily, both correct | Merge unique content into canonical, `git rm` subsumed |
| **Replace** | Old entry now misleading, successor exists / can be written | Write replacement entry, `git rm` old |
| **Delete** | Code gone AND problem domain gone | `git rm` (preferred over stale-flag for truly obsolete) |

For **autofix mode** ambiguity: mark as stale via `flowctl memory mark-stale` instead of guessing.

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
 - Memory schema reference (`flowctl.py:3679-3737`):
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

## Mark stale (autofix ambiguous + Replace-insufficient)

**Not** one of the 5 outcomes — it's the autofix-mode escape hatch and the Replace-insufficient-evidence fallback. Surface in the report under "Marked stale" with the reason.

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

```
Is the entry's referenced code AND problem domain both gone?
 yes → Delete (auto-applicable when ALL auto-Delete criteria hold)
 no → continue

Does another entry in the same module/category overlap heavily?
 yes → Consolidate (canonical = newer/broader; subsumed → merged + git rm)
 no → continue

Does the body's recommended solution conflict with current code?
 yes → enough evidence to write successor?
 yes → Replace (sequential subagent writes new; orchestrator deletes old)
 no → mark stale (autofix) or ask user (interactive)
 no → continue

Are there reference drifts (paths, modules, links, snippets)?
 yes → Update (write tool; preserve unknown frontmatter)
 no → Keep (no edit; report under "Reviewed without edits")
```

In autofix mode, replace any "ask user" branch with mark-stale.
