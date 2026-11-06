# Spec dependency cycle detection

## Goal & Context

A circular dependency between specs goes unnoticed today. `flowctl spec add-dep` accepts an edge that closes a cycle, and nothing downstream rejects it: the specs on the cycle simply never become ready, so `ready`, `next` and `flow --auto` skip them silently. Chart checks its decision graph and `validate` checks task cycles inside one spec, but nothing checks the graph between specs. [paraphrase]

This matters most for teams that split epics into stories (one story per spec), where product managers regularly produce stories whose dependencies loop back on each other. The split is made by an agent through capture's split proposal, and the model proposes the edges, so a cyclic proposal is written edge by edge without complaint. [paraphrase]

The fix stays small: no new verbs, no new machinery, no added wall-clock time on the normal paths. [paraphrase]

<!-- Source: 10% user / 75% [paraphrase] / 15% [inferred] -->

## Architecture & Data Models

- Spec-to-spec edges live in each spec's `depends_on_epics` list. `spec add-dep` is the only command that adds an edge; capture's split, refine's split, plan and goal mode all add edges through it. Tracker sync only reads edges. So one check inside `add-dep` covers every writing path. [inferred]
- The cycle check reads the `depends_on_epics` lists of all specs (both spec layouts, tracker-keyed ids included), adds the proposed edge, and looks for a path from the new dependency back to the dependent spec. The same graph walk serves the whole-graph check in `validate --all`. [inferred]
- `/flow-next:deps` keeps its single gather and its jq pipeline. Classifying causes happens in the same jq pass over the cached gather. [paraphrase]

## API Contracts

`flowctl spec add-dep <spec> <dep> --json`, when the edge would close a cycle (edge direction "spec depends on dep"; the path follows that direction and ends where it started). Exit 1, nothing written: [paraphrase]

```json
{"success": false, "error": "Dependency cycle: fn-1-a -> fn-2-b -> fn-1-a", "code": "dependency_cycle", "cycle": ["fn-1-a", "fn-2-b", "fn-1-a"]}
```

Text mode prints `Error: Dependency cycle: fn-1-a -> fn-2-b -> fn-1-a` to stderr, exit 1. A self-edge is a cycle of length one: `fn-1-a -> fn-1-a`, same code. [inferred]

`flowctl validate --all --json` gains one field, plus one `root_errors` line per cycle, `Spec dependency cycle: <path>`. Any cycle makes `valid` false and exits 1: [paraphrase]

```json
{"spec_cycles": [["fn-1-a", "fn-2-b", "fn-1-a"]]}
```

The `/flow-next:deps` `.deadlocked[]` entries keep `id`, `status` and `unresolved_deps` and gain `cause`, plus `cycle` when the cause is a cycle: [paraphrase]

```json
{"id": "fn-1-a", "status": "open", "unresolved_deps": ["fn-2-b"], "cause": "cycle", "cycle": ["fn-1-a", "fn-2-b", "fn-1-a"]}
{"id": "fn-3-c", "status": "open", "unresolved_deps": ["fn-9-gone"], "cause": "missing"}
{"id": "fn-4-d", "status": "open", "unresolved_deps": ["fn-1-a"], "cause": "blocked"}
```

## Edge Cases & Constraints

- A done dependency stays satisfied, as today; a cycle that runs through a done spec still blocks nothing in `/flow-next:deps`, but `add-dep` and `validate --all` report it, because the graph is wrong either way. [inferred]
- Each cycle is reported once in `validate --all`, not once per member spec. [inferred]
- An edge that already exists stays an idempotent no-op success, as today, even when the graph on disk already holds a cycle. [inferred]
- No added wall-clock time: `add-dep` reads the spec JSON files it needs and nothing else (no task inventory, no git); `/flow-next:deps` adds no flowctl call. [paraphrase]
- Tracker sync keeps mirroring every edge, cycles included, as "is blocked by". A cycle that arrived before this change shows up there as two issues blocking each other, which is the deliberate signal for anyone who bypasses the check. [paraphrase]

## Acceptance Criteria

- **R1:** `spec add-dep` refuses an edge that closes a cycle of length 1 (self), 2, or 3+, with the error and JSON shape in API Contracts; the graph on disk is unchanged after the refusal. Errors: unknown spec ids and invalid ids keep their current messages, checked before the cycle check. [paraphrase]
- **R2:** Valid edges, diamonds (two paths to one dependency), and long acyclic chains (more than 10 deep) still pass `add-dep`; no false positives. Errors: no error surface beyond R1. [paraphrase]
- **R3:** `validate --all` lists every spec dependency cycle already on disk (written by older versions or by hand) in `spec_cycles` and `root_errors`, and exits non-zero. A repo with no cycles produces `spec_cycles: []` and no new errors. Errors: a spec whose `depends_on_epics` is malformed keeps its existing per-spec error and is skipped by the cycle walk. [paraphrase]
- **R4:** Capture's split proposal checks the proposed edge set, including edges the user adds or changes before approving, before any spec is created. A cyclic set is shown to the user with its path, and `split-as-proposed` is not offered until the edges are acyclic, so a split never writes half its specs or edges and then fails. Errors: `add-dep` stays the backstop if a cycle slips through. [paraphrase]
- **R5:** `/flow-next:deps` places every acyclic chain in `.phases`, whatever its depth, by iterating until no spec is added instead of a fixed 10 rounds. [paraphrase]
- **R6:** Each `/flow-next:deps` `.deadlocked[]` entry names its cause (`cycle` with the path, `missing` for a dependency that is not among the specs, `blocked` for a spec held only by another deadlocked spec), the report table shows the cause per row instead of a guessed "likely cause", and existing fields keep their meaning. Errors: a spec that is on a cycle and also has a missing dependency reports `cycle`; the missing id stays visible in `unresolved_deps`. [paraphrase]
- **R7:** Tests in the repo's existing style cover R1-R6. `docs/flowctl.md` and the CHANGELOG describe the new refusal and the `validate --all` field; the Codex skill mirror is regenerated per repo convention. [paraphrase]

## Boundaries

- Tracker sync's cycle tolerance stays as it is. [paraphrase]
- No new flowctl verb, flag or config key; no Mermaid rendering of cycles (the path line is the picture). [paraphrase]
- Single-spec `validate --spec` gains no cross-spec cycle check. [inferred]
- No intake of tracker ideas or epics, no tracker subtask projection, no technology-boundary split. [paraphrase]

## Decision Context

The check sits in `add-dep` because every writer goes through it, so one guard closes every path, capture's and refine's splits included. A separate pre-write validator for each skill would duplicate it. The whole-graph check extends `validate --all` (0.7s on a 315-spec repo) rather than adding a verb. Depth past 10 is fixed by iterating to a fixpoint rather than being reported as a new cause, because it was never a real deadlock. Capture's proposal check is a sentence of guidance over a small graph the agent already holds; `add-dep` catches anything it misses. The refusal is a gating check under G4: it prevents specs from silently never becoming ready in unattended runs. [paraphrase]
