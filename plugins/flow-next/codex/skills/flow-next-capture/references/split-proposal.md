# capture - split proposal machinery (R11) (loaded on demand)

> Loaded ONLY when the §2.5 tripwire trips. The rule itself (tripwire, counting rule,
> independence partition, what a proposal contains) lives in the shared routing reference
> [`spec-count.md`](../../flow-next-flow/references/spec-count.md); this file owns only
> capture's machinery around it. Below the tripwire, normal captures never read either file.

Contents:

- [2.5 - Spec count](#25--spec-count)
- [Phase 4 — split option at read-back](#phase-4--split-option-at-read-back)
- [5.2b — Split branch](#52b--split-branch-interactive-split-as-proposed-only)
- [Phase 6 — split footer](#phase-6--split-footer)

---

## 2.5 - Spec count

Read [`spec-count.md`](../../flow-next-flow/references/spec-count.md) and apply it to the drafted criteria. When its partition yields N>1, compute `SPLIT_PROPOSAL` exactly as that file's "When the partition yields N>1" section describes (per proposed spec: short title, allocated criteria, dependency edges). The skill **never auto-splits** - the user decides at Phase 4.

---

## Phase 4 — split option at read-back

Print the allocation in full (per-spec titles, criteria, dependency edges), then ask the substantive choice once: `split-as-proposed`, `keep-one-spec`, or `abort`. Recommend the proposed split on its independent outcomes, not on inferred content. A cohesive single spec needs no question. This choice occurs before any spec is allocated; abort leaves the temporary draft only.

## 5.2b — Split branch (interactive `split-as-proposed` only)

After the split choice, compose each complete body at its own literal draft path and source-check it. Run the §5.2 create ceremony once per spec in dependency order. There is no second approval of the composed bodies. After all bodies and dependency edges exist, print one saved-spec summary per body and make the §5.6a editor offer once for the set. The user can edit the actual saved specs.

Body composition rules:

- **Each spec gets its own complete body**: its allocated criteria renumbered from R1, the Phase 2 sections that serve those criteria, a per-spec slice of `## Conversation Evidence`, and a short `## Decision Context` note naming the sibling specs and the shared origin. Specs are handover objects — never write "see the other spec" in place of content a worker needs.
- **Per-slice `[user]` findability (before each write):** re-run the §4.1 findability check against each composed body's OWN evidence slice — the combined-draft check does not cover the slicing. A `[user]` line whose supporting quote landed in a sibling's slice gets that quote copied into this spec's slice (evidence lines, like cross-cutting requirements, may appear in every slice they support); only a quote that exists in no slice retags the line. A split body written with a `[user]` line its own slice cannot support has broken this.
- **Cross-cutting requirements** (one constraint governing several specs, e.g. shared middleware) are duplicated into every spec they constrain — never allocated to a single spec, which would create an implicit dependency.
- **User-stated process requirements** (tests green, docs updated) are honored per spec — carried in each spec's body prose or Quick commands, not as counted R-IDs (they were excluded from the §2.5 count for the same reason). When the repo has `.flow/criteria.md`, note that a recurring process statement is standing-criterion material.
- `BIZ_SIGNAL_CATEGORIES` (§2.6) is conversation-level: reuse the single computed value for every spec's Phase 6 judgment — never recompute per spec slice.
- **After all creates, record the edges**: `"$FLOWCTL" spec add-dep <dependent-id> <dependency-id> --json` per proposed edge.
- §5.4–§5.10 follow after all creates and edges: one editor offer for the set, then the remaining follow-ups per spec. The readiness question may cover the set explicitly; one answer applies to all named specs or none, never to an unnamed sibling.
- Phase 6 lists every created id plus the dependency edges.

Autofix never reaches this branch (it records the proposal instead).

---

## Phase 6 — split footer

On the `split-as-proposed` path, emit the footer block once PER created spec (each with its own `Spec captured at…`, its own mandatory `Tracker sync:` line — the sync check ran per spec — and its own next-step hint), followed by one shared line listing the dependency edges.

Each per-spec footer block also carries its own mandatory `Recommended next:` line, judged per spec under the base-footer rule (workflow.md §Phase 6) from [`plan-vs-no-plan.md`](../../flow-next-flow/references/plan-vs-no-plan.md) - each created spec is its own route, and under `from:flow` §5.9b applies per spec. Recommendations are per-spec only; the shared dependency-edge line owns execution order.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

If §2.5 proposed N>1 AND the user picked `keep-one-spec` (declining the split), append:

```text
Note: a <N>-spec split was proposed and declined — the allocation is preserved
in this conversation; $flow-next-refine <id> can still split later.
```

## Forbidden behavior (split row)

| Forbidden | Why |
|-----------|-----|
| Auto-splitting an 8+ acceptance spec | Phase 4 surfaces the option; the user decides. Capture never auto-actions a split. |
