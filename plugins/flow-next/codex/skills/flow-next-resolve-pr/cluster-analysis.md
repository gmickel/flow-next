# Cross-Invocation Cluster Analysis

Reference for Phase 3 of [workflow.md](workflow.md). Defines the gate logic, categorization, and cluster-dispatch rules used to detect recurring feedback patterns across multiple review rounds.

## Purpose

Detect recurring feedback patterns across multiple review rounds. When reviewers flag the same concern category *and* the same file/subtree across rounds, broader investigation is warranted rather than another surgical fix.

First-round feedback is always dispatched individually — there is no prior signal. The cluster analysis only fires once a PR has accumulated at least one resolved thread from a previous round of `/flow-next:resolve-pr`.

## Gate (both must pass)

1. **Signal stage** — `FEEDBACK_JSON.cross_invocation.signal == true`. At least one resolved thread exists on the PR. First-round reviews always fail this stage.
2. **Spatial-overlap precheck** — at least one new `review_thread` shares an exact file path *or* directory subtree with a thread in `FEEDBACK_JSON.cross_invocation.resolved_threads`.

If the signal stage passes but the resolved threads don't carry file paths (older GraphQL responses), signal stage governs alone and the precheck is skipped.

Only inline `review_threads` participate in the precheck. `pr_comments` and `review_bodies` have no file paths and are always dispatched individually — they never join or form clusters.

## Why gated

Single-round clustering (grouping new-only threads by theme) has too many false positives — reviewers routinely surface N related-but-distinct concerns in a single review pass. Cross-round evidence (prior-resolved *plus* new) is the much stronger "this is systemic" signal.

First-round "one helper would fix these" opportunities are handled individually. If the same theme re-emerges a round later, the pattern triggers clustering naturally — no need to guess on the first pass.

## Categorization

Assign each participating item (new threads + previously-resolved threads) exactly one category from this fixed enum:

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

Pick the most specific fit. When a thread straddles two categories, prefer the one that better predicts a shared fix (e.g., `validation` over `error-handling` when the thread is about missing input checks).

## Cluster formation

Two items form a potential cluster when **all three** hold:

- Same concern category, AND
- Spatially proximate (same file, OR files in the same directory subtree), AND
- Cluster contains ≥1 previously-resolved thread

| Thematic match | Spatial proximity | Contains prior-resolved? | Action |
|---|---|---|---|
| Same category | Same file or subtree | Yes | **Cluster** |
| Same category | Same file or subtree | No (new-only) | No cluster |
| Same category | Unrelated locations | Any | No cluster |
| Different categories | Any | Any | No cluster |

A single cluster may contain multiple new threads plus one or more prior-resolved threads. Greedy merging is fine — if two candidate clusters share a new thread, merge them.

## Cluster brief

Synthesize one brief per cluster. The brief is passed verbatim to the resolver agent as `cluster_brief` input (see `agents/pr-comment-resolver.md` § Cluster mode):

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

The brief empowers the resolver to read the broader area and decide between:

- **Holistic fix** — one refactor addresses all threads in the cluster (extract a shared validator, introduce a consistent error type, etc.).
- **Individual fixes** — still address each thread separately, but with awareness of the broader pattern.

Both outcomes are valid. The resolver's `cluster_assessment` field reports which path was taken and why.

## Dispatch boundary for previously-resolved threads

Previously-resolved threads provide **cluster-brief context only**. They are NEVER individually re-dispatched — they were already resolved in prior rounds and should stay that way.

If a previously-resolved thread doesn't cluster with any new thread, it is dropped silently — it provided candidate context but no cross-round pattern emerged.

## Non-cluster items

Items outside any cluster are dispatched individually as `review_threads` / `pr_comments` / `review_bodies` per the standard flow in Phase 5 of workflow.md. `pr_comments` and `review_bodies` always fall into this bucket regardless of cluster analysis outcome.

## No-cluster fallback

If no clusters are identified after analysis (signal fired but no new-thread-with-prior-resolved pattern materialized), proceed with all items as individual. The only cost incurred was the analysis itself — no harm done.

## `--no-cluster` override

The user flag `--no-cluster` skips this entire phase. All new items go individual. Useful when:

- The user wants speed on a small PR where clustering overhead isn't worth it.
- The user knows the review is one-shot (e.g., a specific reviewer who only commented once).
- The user is debugging and wants deterministic per-thread behavior.

`--no-cluster` is equivalent to forcing the gate to fail — Phase 3 is a no-op.
