# GitHub tracker transport shape

Flowctl uses authenticated GitHub CLI transport. The provider adapter constructs
argv, supplies JSON bodies through stdin, normalizes responses, and classifies
failures. Skill prose never executes GitHub API requests directly.

## Addressing

- destination: resolved repository owner/name;
- durable issue identity: node id;
- display identity: `#N`;
- parent verification: issue read returns the node id;
- comment response parent identity: unavailable, so no response-side parent
 assertion is invented.

## Operation mapping

| Normalized operation | GitHub shape |
|---|---|
| issue read/update | repository issue endpoint |
| comments | issue comments collection |
| labels | issue labels |
| assignees | issue assignees |
| status | open/closed state plus configured project/status policy |
| list-open | repository issues filtered by configured ready label |
| relation projection | sub-issue hierarchy proxy with structured degradation |
| relation-list | validated empty dependency set; hierarchy is not blocked-by |
| attachment | unsupported capability |

Issue bodies and comments are Markdown. Pagination is completed inside flowctl.
Pull requests are not treated as issues in the ready lane.

## Capability degradation

GitHub attachment upload is unsupported. GitHub issues expose parent/sub-issue
hierarchy but no issue-level blocked-by relation. Projection may use that
hierarchy as a visibly degraded proxy and records it in Flow's provenance
ledger. The backlog `relation-list` read deliberately returns no dependency
rows after validating the parent: hierarchy can express decomposition or
ownership and must never be normalized as `type: blocks`.

All mutations validate the issue node id before writing. A moved, deleted, or
reused display number produces a structured stale/not-found/conflict result and
does not mutate local link state.
