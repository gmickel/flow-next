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

- **Summary-payload split note** - one short clause, e.g. `Split: 11 criteria across 2 independent outcomes - split proposed, allocation printed above.` or `Split: 12 criteria, one cohesive outcome - single spec recommended.` When `SPLIT_PROPOSAL` has N>1, the printed read-back message (Step A) includes the full proposal block after the summary: per-spec titles, allocated criteria, dependency edges. The allocation prints in full because the user ratifies it; the draft bodies do not.
- **Extra option** (only when §2.5 proposed N>1), added to the frozen §4.2 list: `split-as-proposed` — Phase 5 runs the create ceremony once per proposed spec and records the dependency edges (§5.2b); "you get N linked specs exactly as printed above".
- **Recommendation precedence:** when a `SPLIT_PROPOSAL` with N>1 exists, the recommendation leads with `split-as-proposed` - it takes precedence over a zero-`[inferred]` `Recommended: approve and write` (proposing structure is not self-blessing content; the no-self-blessing rule still governs `[inferred]` content): `Recommended: split-as-proposed - <N> independently shippable outcomes (allocation printed above). Confidence: [<tier>].`
- **Forbidden:** never auto-split. N specs are written only through the user picking `split-as-proposed`; `approve and write` writes exactly one spec, and autofix never splits (see `references/autofix-mode.md` §4.4 when that mode is active).

---

## 5.2b — Split branch (interactive `split-as-proposed` only)

**Compose first, summarize, then write.** The user ratified an allocation table, not the N bodies - so before any flowctl write:

1. Compose every spec body (rules below), each at its own literal draft path — `${TMPDIR:-/tmp}/flow-capture-draft-<that-spec's-title-slug>-<same suffix as §4.1>.md` (per-spec slug, shared suffix).
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

2. **Print one compact summary per body** as an ordinary assistant message (title, criteria count, source tally, `Recommended next:` per §2.8 judged per spec, draft path - the read-back contract's payload; a full body prints only on request), then ONE short `plain-text numbered prompt` - header `Write N specs?`, body: one-line pointer + per-spec title list; options: `approve and write` (proceed), `open in editor` (hand the N draft files to the editor; re-read each before asking again), `back` (return to the §4.2 read-back with the proposal still on offer); free text edits one body, diff printed. Content ratified in the combined draft needs no re-scrutiny prose - this ask exists because the slicing (renumbering, evidence slices, sibling notes) is new authored text the user has not seen.
3. On `approve and write`, run the §5.2 new-spec ceremony once per spec, in dependency order (dependencies first).

Body composition rules:

- **Each spec gets its own complete body**: its allocated criteria renumbered from R1, the Phase 2 sections that serve those criteria, a per-spec slice of `## Conversation Evidence`, and a short `## Decision Context` note naming the sibling specs and the shared origin. Specs are handover objects — never write "see the other spec" in place of content a worker needs.
- **Per-slice `[user]` findability (before the step-2 ask):** re-run the §4.1 findability check against each composed body's OWN evidence slice — the combined-draft check does not cover the slicing. A `[user]` line whose supporting quote landed in a sibling's slice gets that quote copied into this spec's slice (evidence lines, like cross-cutting requirements, may appear in every slice they support); only a quote that exists in no slice retags the line. A split body written with a `[user]` line its own slice cannot support has broken this.
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

Each per-spec footer block also carries its own mandatory `Recommended next:` line, judged per spec under the base-footer rule (workflow.md §Phase 6) from [`plan-vs-no-plan.md`](../../flow-next-flow/references/plan-vs-no-plan.md) - each created spec is its own route, and under `from:flow` §5.9b applies per spec. Recommendations are per-spec only; the shared dependency-edge line owns execution order.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

If §2.5 proposed N>1 AND the user picked `approve and write` (declining the split), append:

```text
Note: a <N>-spec split was proposed and declined — the allocation is preserved
in this conversation; $flow-next-interview <id> can still split later.
```

## Forbidden behavior (split row)

| Forbidden | Why |
|-----------|-----|
| Auto-splitting an 8+ acceptance spec | Phase 4 surfaces the option; the user decides. Capture never auto-actions a split. |
