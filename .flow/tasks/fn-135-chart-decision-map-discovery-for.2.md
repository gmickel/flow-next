---
satisfies: [R6, R7, R10, R20, R21, R22, R23, R28, R40, R44, R48, R53]
---
# fn-135-chart-decision-map-discovery-for.2 Implement immutable resolution and supersession cascades

## Description
### Objective

Complete the local decision state machine: safe asset attachment, resolve, out-of-scope, immutable supersession, direct/transitive premise invalidation, ledger projection, and abandonment. Preserve every paid-for answer and prototype artefact, make reversals mechanically safe, and prevent a prototype from resolving without reviewable evidence.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` — add idempotent `attach-asset`, resolve, out-of-scope, abandon, dependent-closure, replacement-D-ID, ledger update, asset validation, and transition-note operations on the task-1 transaction layer.
- `plugins/flow-next/tests/test_chart_resolution.py` — new state-transition, open-decision asset attachment, prototype proof, resolve-with-graduation, ledger, cascade, safe-evidence, rollback, and idempotency suite.
- `plugins/flow-next/tests/test_chart_store.py` and `test_chart_graph_claims.py` — extend only shared transaction/error fixtures if needed.

### Investigation targets

- Keep one authoritative detailed answer in the decision record; the chart body receives only a one-line gist and link.
- Reuse the append-only identity discipline from R-IDs/spec history. Do not mutate an old resolved answer or reuse a D-ID.
- Treat `depends_on` as a premise graph. On supersession, walk its direct and transitive closure. An open dependent stays open, loses its claim, and gets a transition note. A resolved dependent stays immutable and gets a new replacement D-ID that supersedes it.
- `--keep-dependents` is an explicit judgment override and must be recorded on both the new decision and every affected dependent.
- `--graduation-file` describes new titled/typed decisions, their wiring, and parked-question keys to remove. Allocate/validate the entire post-resolution graph and commit answer, ledger, new records, wiring, and removals as one journalled transaction.
- Asset inputs are structured safe references with kind/reference/display summary and revision or fingerprint where the source provides one. Accept repository-relative paths, branch/commit refs, and approved HTTPS tracker/evidence URLs; reject ignored or missing paths, symlink escapes, paths outside the repo, redirects used as identity, and credential-bearing URLs.
- `attach-asset` persists an artefact before resolution while leaving the D-ID open. Identical retries are no-ops; a conflicting reuse is explicit. For `prototype`, `resolve` requires at least one attached safe asset. Human reaction remains a skill-owned attended judgment in task 4, but deterministic plumbing must make artefact-free prototype resolution impossible.
- An interruption after attachment leaves the asset and open decision resumable. A later session presents the same reference/revision without rebuilding it; attach alone never writes an answer, closes the D-ID, or promotes prototype code into implementation.
- If answer input contains an obvious secret or literal guard-triggering destructive command, refuse to embed it. Preserve the original only by approved evidence reference; store a safe redacted/escaped summary and link. Never silently strip or rewrite the source.

### Required behavior and examples

- Resolving `fn-N.D4` writes its answer once and appends exactly one linked gist to `## Decisions`; retry with identical inputs is idempotent, conflicting retry is `invalid_state`.
- `resolve fn-N.D9 --supersedes D3` keeps D3 readable, strikes its ledger line, sets bidirectional links, and reports all affected D-IDs.
- If resolved D7 depended on D3, create a fresh decision such as D10 with D7's question and an explicit “re-evaluate after D9 superseded D3” reason; never reopen D7 in place.
- `out-of-scope` adds one boundary reason and no decision-ledger answer.
- `abandon --reason` closes the chart as `abandoned` with the reason recorded and no record deleted.
- Resolve can remove a parked question and create/wire the newly visible decisions in the same commit; a crash or validation error leaves all of it untouched.
- `attach-asset fn-N.D6` records the throwaway artefact and its revision while D6 stays open. Resolving D6 without any asset fails validation; after the attended reaction, resolve records the answer against the already-linked artefact.
- If the session ends between attachment and reaction, D6 remains open with the same asset. Retry presents it again; it does not create a duplicate asset or infer approval.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_chart_resolution -q
```

### Non-goals

- No agent decision selection or newly-visible decision inference; the skill owns those judgments and supplies the graduation file.
- No briefing/capture or tracker transport.
## Acceptance
- Legal transitions are enforced exactly; resolved answers and D-IDs are immutable and retries are idempotent only when inputs match.
- Resolve updates decision record and compact ledger in one recoverable transaction; the map never duplicates the full answer.
- Supersession preserves the old record, strikes/links its ledger line, walks direct and transitive `depends_on`, clears open claims, and creates replacement D-IDs for resolved dependents.
- `--keep-dependents` records the override and reports the complete affected set without cascading.
- Resolve-with-graduation atomically publishes newly visible titled decisions/wiring and removes parked questions; invalid graph or killed process recovers without partial graduation.
- Out-of-scope and abandon preserve history and write only their documented projections.
- Unsafe/secret-bearing answer content is refused for embedding and remains available only through an approved source reference plus safe summary; answer, asset, and ledger tests cover it.
- Asset attachment is transactional and idempotent; safe references/revisions survive interruption while the decision remains open.
- Prototype resolution requires a persisted safe artefact and refuses an empty, unavailable, or unsafe reference. Attachment alone never records human reaction, resolves the D-ID, or turns prototype code into implementation.
- Focused commands pass: `cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_chart_graph_claims test_chart_resolution -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
