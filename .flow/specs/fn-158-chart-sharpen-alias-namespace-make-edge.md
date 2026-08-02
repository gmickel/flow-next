# Chart sharpen alias namespace: make edge references decidable

## Goal & Context
<!-- scope: business -->

Split out of fn-153 at plan-review round 3. fn-153's goal binds it to "two narrow correctness fixes in one module, no new surface, no behavior anyone is currently relying on", and three review rounds established that the resolve-sharpen alias namespace cannot be fixed inside that constraint: every candidate fix changes public input semantics.

This is the design spec that constraint deferred. It is **not** a correctness patch, and it should not be planned as one.

**The user-visible problem.** When `chart resolve --sharpen-file` adds decisions, an edge reference like `"3"` or `"d3"` may resolve to an already-persisted decision or to one of the incoming decisions, **depending on how many decisions the chart already has**. A caller cannot know which without counting. Wrong resolution is silent: the graph validates, persists, and answers later supersession and briefing questions with the wrong edges.

## Architecture & Data Models
<!-- scope: technical -->

Three findings from the fn-153 review rounds, all verified against the code. Any design here must answer all three.

**1. The shadowing is index-dependent.** The sharpen new-decision loop writes batch aliases (`flowctl.py:13847-13852`), then the existing-decision fold overwrites them (`13866-13871`). On a chart holding D1 and D2, incoming #1 and #2 lose `1`/`d1` and `2`/`d2` to the persisted pair - but sharpen five decisions onto that chart and indices `3`, `4`, `5` have no persisted counterpart and still resolve to the incoming ones. So `<n>` means "persisted decision n" or "the nth incoming decision" as a function of chart size.

**2. Removing an alias from the map does not make it unreachable.** `_normalize_edge_refs` (`11345-11378`) falls through to `canonicalize_decision_id(text, chart_id=chart_id)` at `11376` when a lookup misses. So dropping `3` / `d3` from `local_map` does not stop `"3"` from resolving - it canonicalizes straight to `<chart-id>.D3`, which on a sharpened chart is the incoming decision. **This is why fn-153's first attempt at R5 would not have worked even though it looked correct.** Any namespace policy has to control the fallback, not just the map.

**3. There is a third tier of decisions.** A single `chart resolve` may both supersede and sharpen. Cascade-created replacement decisions are added to `by_id` **before** the sharpen block runs, so they are neither persisted-at-entry nor incoming. Whether their `<n>` / `d<n>` / full-ID forms are addressable is currently undefined, and an error schema with only `incoming` / `persisted` claimants cannot describe a collision involving one.

**4. The provisional pass complicates identity.** `validate_and_build_initial_map` runs twice per create (`23329` with a sentinel chart id, `23345` after real allocation). Full-D-ID aliases depend on the chart id, so any validation of that alias form has to know which pass it is in. Sharpen has no equivalent sentinel, but a shared helper across both paths will meet this.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A caller can determine what an edge reference resolves to from the reference alone, without knowing how many decisions the chart already holds. The chosen policy is documented in `plugins/flow-next/docs/flowctl.md` with the persisted / incoming / cascade-replacement tiers named explicitly.
- **R2:** The policy controls resolution end to end, including the `canonicalize_decision_id` fallback at `flowctl.py:11376` - proven by a real-CLI test that a reference the policy makes unavailable does **not** silently resolve through the fallback.
- **R3:** Cascade-created replacements have a defined tier: either addressable with stated alias forms and ordering, or full-D-ID only. A combined `--supersedes` plus `--sharpen-file` test exercises it, and the error schema can name a collision involving one.
- **R4:** The change is released as a **deliberate, documented break** in public input semantics, with the migration stated: which reference forms stop working, what replaces them, and how a caller rewrites an existing sharpen payload. `/flow-next:chart` needs no change (the skill never emits explicit ids and never references batch ordinals), so the blast radius is direct `flowctl chart` callers only.
- **R5:** Alias-collision validation covers the sharpen path with the same owner-based definition fn-153 establishes for initial-map, including the new-versus-new case (two co-arriving sharpen decisions claiming one explicit `id`) and the new-versus-persisted case.

## Boundaries
<!-- scope: business -->

- **Depends on fn-153 landing first.** fn-153 establishes the collision definition, the `alias_collision` error code and its `details` schema for the initial-map path. This spec extends that vocabulary to sharpen rather than inventing a second one.
- **Not a migration of existing charts.** Charts already on disk keep whatever graph they were written with; there is no `chart doctor` and this spec does not add one.
- **Not the cascade-ordering fix.** That is fn-153 R1/R6/R7 and is independent.

## Decision Context
<!-- scope: both -->

**Why this is a design spec and not a bug fix.** A bug fix restores intended behavior. Here there is no intended behavior to restore: the sharpen namespace was never specified, and the three tiers plus the canonicalization fallback interact in ways no current document describes. Deciding what a reference *should* mean is the work, and it is a public-semantics decision with a migration attached.

**Why fn-153 could not absorb it.** fn-153's goal says "no new surface, no behavior anyone is currently relying on." Every candidate fix for sharpen breaks that clause. Attempting it inside fn-153 produced two mechanisms that did not work (one rejected every sharpen batch; one left the aliases reachable through the fallback) before the constraint was noticed.

## Quick commands
<!-- scope: technical -->

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution test_chart_graph_claims -q
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

## References

- Sharpen aliasing: `flowctl.py:13814-13872` (new-decision writes `13847-13852`, existing fold `13866-13871`)
- Fallback: `_normalize_edge_refs` `11345-11378`, fallback at `11376`; `canonicalize_decision_id`
- Cascade replacements enter `by_id` before sharpen: `resolve_chart_decision` `13625-13785`
- Provisional double-call: `cmd_chart_create` `23329` / `23345`
- Initial-map counterpart landing in fn-153: `validate_and_build_initial_map` `11814-11896`
