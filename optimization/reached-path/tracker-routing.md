# Tracker Sync reached-path candidate

Task `fn-130-reached-path-skill-prompt-optimization.4`.

## Lineage and safety

- Structural baseline: `V1/B1` at `8ed71a73ccc593a8a018dcdb805a86f396dcf76f`.
- Pre-edit input check: `python3 optimization/reached-path/run_eval.py --check-b1-input tracker` → `OK: tracker inputs match B1 (13 files)`.
- Candidate comparison: B1 only; never B0.
- Transport proof: `optimization/reached-path/tracker_routes.py` records fake calls using markers from the selected canonical adapter reference. It executes no command, opens no network connection, and records `external_writes: 0`.
- Unknown/malformed and no-transport routes stop safely with no adapter and a fake `noop` receipt.

## Selected routes

Common path for configured runs: `steps.md`, `adapter-interface.md`,
`body-merge.md`, `status-sync.md`, `comments-sync.md`, and `identity.md`.
Exactly one provider path is added:

| Route | Added adapter path |
|---|---|
| inactive / malformed | none |
| Linear MCP | `linear-ladder.md` + `linear-mcp.md` |
| Linear GraphQL | `linear-ladder.md` + `linear-graphql.md` |
| Linear no transport | `linear-ladder.md` only |
| GitHub | `github.md` |
| GitLab | `gitlab.md` |
| Jira | `jira.md` |

## Deterministic reached-path result

Frozen algorithm: LF normalization; full root once; full successfully reached
direct reference once per path+hash. Backend/cache telemetry is not substituted
for this source-size measure.

| Route | B1 chars | Candidate chars | Reduction |
|---|---:|---:|---:|
| inactive | 452,552 | 228,459 | 224,093 (49.5%) |
| malformed | 452,552 | 228,459 | 224,093 (49.5%) |
| Linear MCP | 452,552 | 258,355 | 194,197 (42.9%) |
| Linear GraphQL | 452,552 | 262,879 | 189,673 (41.9%) |
| Linear no transport | 452,552 | 243,811 | 208,741 (46.1%) |
| GitHub | 452,552 | 268,063 | 184,489 (40.8%) |
| GitLab | 452,552 | 289,140 | 163,412 (36.1%) |
| Jira | 452,552 | 302,354 | 150,198 (33.2%) |

## Zero-loss matrix

The frozen fixture inventory remains 15/15: inactive, malformed, Linear MCP,
Linear GraphQL, GitHub, GitLab, Jira, push, pull, reconcile,
create-if-unlinked, and body/status/comments/dependency conflicts. The common
spine and normalized nine-method contract are unchanged; only adapter loading
is routed. Fake traces assert production-shaped `save_issue`, Linear GraphQL,
`gh`, `glab`, and Jira REST markers originate in the selected adapter reference.
Existing state/GitLab/Jira/mirror suites cover identity, backlog, receipts,
auth/no-op, and reconciliation plumbing.

Verdict: **keep**. Every structural route reduces reached-path size; no
zero-loss cell was reverted. Codex mirror regeneration is conductor-owned for
the combined parallel wave.
