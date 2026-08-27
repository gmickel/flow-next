# capture — spec-count heuristic + split proposal (R11) (loaded on demand)

> Loaded ONLY when the §2.5 tripwire trips: **8+ acceptance criteria**, OR the criteria visibly serve
> more than one independently shippable outcome. Below the tripwire, normal captures see nothing and
> never read this file.

Contents:

- [2.5 — Spec-count heuristic](#25--spec-count-heuristic-how-many-specs-is-this)
- [Phase 4 — split option at read-back](#phase-4--split-option-at-read-back)
- [5.2b — Split branch](#52b--split-branch-interactive-split-as-proposed-only)
- [Phase 6 — split footer](#phase-6--split-footer)

---

## 2.5 — Spec-count heuristic: how many specs is this?

Epics, briefing packages, and multi-feature requests arrive as one conversation but often land best as 1..n specs. After drafting the criteria, judge the count:

**Tripwire (when to compute):** 8+ acceptance criteria, OR the criteria visibly serve more than one independently shippable outcome. Below the tripwire, skip this section entirely — normal captures see nothing.

**Counting rule:** count business and technical requirements only. Standing criteria (G-IDs from `.flow/criteria.md`) and process requirements (tests green, docs updated, mirror synced) never count — they ride along with any spec. Excluded-but-user-stated process items are still honored (R10): carry them in the spec body's prose or Quick commands, not as counted R-IDs.

**Split criterion — independence, not size.** The count trips the check; the partition comes from shippability:

- Would a stakeholder accept this cluster of criteria on its own?
- Do the clusters touch disjoint surfaces?
- Does one cluster depend on infrastructure another builds? A dependency seam is a natural spec boundary.

A large-but-cohesive set (12 criteria, one subsystem, one outcome) is ONE spec — say so in the read-back note and move on. Never pad N to look thorough.

**When the partition yields N>1, compute `SPLIT_PROPOSAL`:** per proposed spec — a short title, the criteria allocated to it, and the dependency edges between the proposed specs (`B depends on A`). Each proposed spec must be self-contained and independently reviewable; one spec = one PR = one completion review judging every R-ID, which is why oversized specs degrade review quality.

The proposal surfaces at the Phase 4 read-back (allocation printed in full, one-line note in the ask). The skill **never auto-splits** — the user decides.

---

## Phase 4 — split option at read-back

- **Summary-payload item 3 — spec-count note** — one short clause, e.g. `11 criteria across 2 independent outcomes — split proposed, allocation printed above.` or `12 criteria, one cohesive outcome — single spec recommended.` When `SPLIT_PROPOSAL` has N>1, the printed read-back message (Step A) includes the full proposal block after the draft: per-spec titles, allocated criteria, dependency edges.
- **Extra option** (only when §2.5 proposed N>1), added to the frozen §4.2 list: `split-as-proposed` — Phase 5 runs the create ceremony once per proposed spec and records the dependency edges (§5.2b); "you get N linked specs exactly as printed above".
- **Recommendation precedence:** when a `SPLIT_PROPOSAL` with N>1 exists, the recommendation leads with `split-as-proposed` — it takes precedence over a zero-`[inferred]` `Recommended: approve` (proposing structure is not self-blessing content; the no-self-blessing rule still governs `[inferred]` content): `Recommended: split-as-proposed — <N> independently shippable outcomes (allocation printed above). Confidence: [<tier>].`
- **Forbidden:** never auto-split. N specs are written only through the user picking `split-as-proposed`; `approve` writes exactly one spec, and autofix never splits (see `references/autofix-mode.md` §4.4 when that mode is active).

---

## 5.2b — Split branch (interactive `split-as-proposed` only)

**Compose first, show, then write.** The user ratified an allocation table, not the N bodies — so before any flowctl write:

1. Compose every spec body (rules below), each at its own literal draft path — `${TMPDIR:-/tmp}/flow-capture-draft-<that-spec's-title-slug>-<same suffix as §4.1>.md` (per-spec slug, shared suffix).
2. **Print all N bodies as ordinary assistant messages** (print-then-ask, same R13 contract as §4.2), then ONE short `AskUserQuestion` — header `Write N specs?`, body: one-line pointer + per-spec title list; options: `write` (proceed), `back` (return to the §4.2 read-back with the proposal still on offer). Content ratified in the combined draft needs no re-scrutiny prose — this ask exists because the slicing (renumbering, evidence slices, sibling notes) is new authored text the user has not seen.
3. On `write`, run the §5.2 new-spec ceremony once per spec, in dependency order (dependencies first).

Body composition rules:

- **Each spec gets its own complete body**: its allocated criteria renumbered from R1, the Phase 2 sections that serve those criteria, a per-spec slice of `## Conversation Evidence`, and a short `## Decision Context` note naming the sibling specs and the shared origin. Specs are handover objects — never write "see the other spec" in place of content a worker needs.
- **Cross-cutting requirements** (one constraint governing several specs, e.g. shared middleware) are duplicated into every spec they constrain — never allocated to a single spec, which would create an implicit dependency.
- **User-stated process requirements** (tests green, docs updated) are honored per spec — carried in each spec's body prose or Quick commands, not as counted R-IDs (they were excluded from the §2.5 count for the same reason). When the repo has `.flow/criteria.md`, note that a recurring process statement is standing-criterion material.
- `BIZ_SIGNAL_CATEGORIES` (§2.6) is conversation-level: reuse the single computed value for every spec's Phase 6 judgment — never recompute per spec slice.
- **After all creates, record the edges**: `"$FLOWCTL" spec add-dep <dependent-id> <dependency-id> --json` per proposed edge.
- §5.4–§5.10 (branch name, tracker sync, glossary, readiness, HTML lens) run per created spec exactly as for a single create; the Phase 4 mark-ready answer applies to all created specs or none.
- Phase 6 lists every created id plus the dependency edges.

Autofix never reaches this branch (it records the proposal instead).

---

## Phase 6 — split footer

On the `split-as-proposed` path, emit the footer block once PER created spec (each with its own `Spec captured at…`, its own mandatory `Tracker sync:` line — the sync check ran per spec — and its own next-step hint), followed by one shared line listing the dependency edges.

Each per-spec footer block also carries its own mandatory `Recommended next:` line, judged per spec under the base-footer rule (workflow.md §Phase 6) against the smallest-sufficient rule in [docs/pipeline-variations.md](../../../docs/pipeline-variations.md) — each created spec is its own route. Recommendations are per-spec only; the shared dependency-edge line owns execution order.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

If §2.5 proposed N>1 AND the user picked `approve` (declining the split), append:

```text
Note: a <N>-spec split was proposed and declined — the allocation is preserved
in this conversation; /flow-next:interview <id> can still split later.
```

## Forbidden behavior (split row)

| Forbidden | Why |
|-----------|-----|
| Auto-splitting an 8+ acceptance spec | Phase 4 surfaces the option; the user decides. Capture never auto-actions a split. |
