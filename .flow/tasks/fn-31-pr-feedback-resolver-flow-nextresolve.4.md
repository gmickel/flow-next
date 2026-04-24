# fn-31-pr-feedback-resolver.4 Cross-invocation cluster analysis

## Description

Dedicated reference file `cluster-analysis.md` defining the gate logic, categorization, and cluster-dispatch rules. Referenced by workflow.md Phase 3.

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-resolve-pr/cluster-analysis.md`

## Content outline

### Purpose

Detect recurring feedback patterns across multiple review rounds. When reviewers flag the same concern category + same file/subtree across rounds, broader investigation is warranted rather than another surgical fix.

### Gate (both must pass)

1. **Signal stage:** `cross_invocation.signal == true` in the fetch output (at least one resolved thread exists — first-round reviews always fail this).
2. **Spatial-overlap precheck:** at least one new `review_thread` shares an exact file path or directory subtree with a thread in `cross_invocation.resolved_threads`.

If signal stage passes but file paths aren't available on resolved threads (older API responses), signal stage governs alone.

Only inline `review_threads` participate in the precheck. `pr_comments` and `review_bodies` have no paths and are always dispatched individually.

### Why gated

Single-round clustering (grouping new-only threads by theme) has too many false positives. Cross-round evidence (prior-resolved + new) is the much stronger "systemic" signal. First-round "one helper would fix these" opportunities handle individually; pattern emerges over rounds and triggers clustering naturally.

### Categorization

Assign each item (new + previously-resolved) exactly one category from this fixed list:

- `error-handling`
- `validation`
- `type-safety`
- `naming`
- `performance`
- `testing`
- `security`
- `documentation`
- `style`
- `architecture`
- `other`

### Cluster formation

Two items form a potential cluster when:
- Same concern category, AND
- Spatially proximate (same file, OR files in same directory subtree), AND
- Cluster contains ≥1 previously-resolved thread

| Thematic match | Spatial proximity | Contains prior-resolved? | Action |
|---|---|---|---|
| Same category | Same file or subtree | Yes | Cluster |
| Same category | Same file or subtree | No (new-only) | No cluster |
| Same category | Unrelated locations | Any | No cluster |
| Different categories | Any | Any | No cluster |

### Cluster brief

Synthesize one brief per cluster, passed to the resolver agent:

```xml
<cluster-brief>
  <theme>[concern category]</theme>
  <area>[common directory path or file]</area>
  <files>[comma-separated file paths]</files>
  <threads>[comma-separated new thread IDs]</threads>
  <hypothesis>[one sentence: what the recurring feedback across rounds suggests about a deeper issue]</hypothesis>
  <prior-resolutions>
    <thread id="PRRT_..." path="..." category="..."/>
    <thread id="PRRT_..." path="..." category="..."/>
  </prior-resolutions>
</cluster-brief>
```

Brief empowers the resolver to read the broader area and decide: holistic fix (one refactor addresses all threads in cluster) vs individual (still address each separately but with awareness).

### Dispatch boundary for previously-resolved threads

Previously-resolved threads provide cluster-brief context only. **They are NEVER individually re-dispatched** — they were already resolved in prior rounds. Only new threads get individual or cluster dispatch.

If a previously-resolved thread doesn't cluster with any new thread, it's dropped — it provided context but no cross-round pattern was found.

### Non-cluster items

Items outside any cluster are dispatched individually as review_threads / pr_comments / review_bodies per the standard flow.

### No-cluster fallback

If no clusters are identified after analysis (signal fired but no new-thread-with-prior-resolved pattern), proceed with all items as individual. Only cost was the analysis itself.

### `--no-cluster` override

User flag skips this entire phase. All new items go individual. Useful when user wants speed or knows the review is one-shot.

## Acceptance

- **AC1:** `cluster-analysis.md` exists at `plugins/flow-next/skills/flow-next-resolve-pr/`.
- **AC2:** Document describes both gate stages explicitly.
- **AC3:** Categorization list is the fixed 11-item enum.
- **AC4:** Cluster formation table covers the four match-combinations.
- **AC5:** Cluster-brief XML shape is documented verbatim.
- **AC6:** Dispatch boundary for resolved threads is clear: context-only, never re-dispatched individually.
- **AC7:** `--no-cluster` behavior documented.

## Dependencies

- fn-31-pr-feedback-resolver.3 (workflow.md references this file)

## Done summary
Added `cluster-analysis.md` reference doc to the `flow-next-resolve-pr` skill. Documents the two-stage gate (cross_invocation.signal + spatial-overlap), 11-category enum, cluster formation table, cluster-brief XML shape, prior-resolved-context-only boundary, and `--no-cluster` override. Already referenced by workflow.md Phase 3 and SKILL.md; all 7 acceptance criteria pass smoke tests.
## Evidence
- Commits: c7f27ae4d3b289e45bc1652f403018dbbc65720d
- Tests: grep-based AC1-AC7 smoke checks against cluster-analysis.md
- PRs: