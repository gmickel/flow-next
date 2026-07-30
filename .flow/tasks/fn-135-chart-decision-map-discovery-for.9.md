---
satisfies: [R3, R4, R5, R14, R17, R23, R26, R36, R37, R38, R39, R43, R44]
---
# fn-135-chart-decision-map-discovery-for.9 Add chart graph, frontier, parked questions, and claims

## Description
### Objective

Layer decision metadata, parked questions, graph wiring, frontier, compact loading, configuration, and audited claims onto the task-1 store. This completes the early lifecycle harness without mixing it into allocator/journal work.

### Exact files

- `plugins/flow-next/scripts/flowctl.py` — add initial-map validation/guarded create, decision create, `title`, derived/explicit `attendance`, park/remove-question, wire-decision, graph validation, frontier ordering, claim/release/break-stale, completion predicate, compact metadata reads, and config reads for `chart.maxDecisions` plus `chart.claimStaleAfter`.
- `plugins/flow-next/tests/test_chart_graph_claims.py` — new parked-question, attendance, graph, frontier, claim, compact-read, and exact-envelope suite.
- `plugins/flow-next/tests/test_config_snapshot.py` — pin chart config defaults and validation through the existing snapshot contract.

### Investigation targets

- Reuse task-start ownership/conflict semantics around `flowctl.py:19885-20070`, but preserve chart-specific `claimed_by`, `claimed_at`, and transition notes.
- `blocked_by` controls readiness; `depends_on` is premise provenance. Reject missing targets, self-edges, duplicates, and cycles atomically before either pair changes.
- `park-question` returns a stable normalized question key. Identical add/remove retries are no-ops only when their enclosing transaction already committed.
- `wire-decision` replaces both edge sets under the chart transaction so two-pass create/wire never exposes an invalid final graph.
- Derive attendance for research/probe/eval/prototype/interview. Require `--attendance attended|unattended` for task decisions. Cost and unattended gates read the stored field.
- Finalize public `chart create --initial-map-file`: validate all initial titled decisions, attendance, edges, and parked questions; compute count/cost; refuse over `chart.maxDecisions` before allocation. `--force-size --reason` records actor, configured ceiling, proposed count, timestamp, and reason in the same create transaction.
- Claiming does not change decision status. Owner release succeeds. Stale break requires age plus reason and records actor/prior owner/age.
- Frontier/status read compact metadata only; tests instrument full-body reads and fail if navigation opens answer/assets.

### Required behavior and examples

- `add-decision --title "Choose tenant key" --type research ...` returns `fn-N.D1`, title, attendance, and record link.
- `add-decision --type task` without attendance fails validation; a human approval task is attended while a scripted export task may be unattended.
- A blocked-only or claimed-only chart is stuck, not complete.
- Open Questions can be persisted without editing Markdown, then removed by stable key during a later atomic sharpening.
- Over-ceiling initial create fails without any chart/id reservation; an explicitly forced create returns the audit object in its v1 result and persists the same object in the sidecar.
- Claim conflicts and stale claims have distinguishable v1 error classes/codes.

### Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_chart_graph_claims test_config_snapshot -q
```

### Non-goals

- No resolution/supersession or briefing.
- No skill-side judgment about which question to create.
## Acceptance
- Every decision stores a title and valid attendance; five types derive it and task requires it explicitly; cost/autonomy tests read that field.
- Park/remove-question and wire-decision are transactional/idempotent and never require direct skill edits.
- Graph validation rejects missing, self, duplicate, and cyclic edges atomically; tests distinguish readiness from premise provenance.
- Frontier returns only open, unblocked, unclaimed decisions in order; blocked-only and claimed-only charts are not complete.
- Claim conflict, owner release, and age-gated stale break have audited metadata and exact v1 result/error fixtures.
- Initial-map create enforces `chart.maxDecisions` before persistence; `--force-size --reason` is required for override and exact tests prove persisted actor/ceiling/count/time/reason audit.
- Human output pairs title/full D-ID/link, and compact list/show/frontier tests prove full answers/assets are not loaded.
- Focused commands pass: `cd plugins/flow-next/tests && python3 -m unittest test_chart_store test_chart_graph_claims test_config_snapshot -q`.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
