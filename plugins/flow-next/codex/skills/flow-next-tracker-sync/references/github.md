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
| relation | native blocked-by when capability exists, otherwise flow-owned body block |
| attachment | unsupported capability |

Issue bodies and comments are Markdown. Pagination is completed inside flowctl.
Pull requests are not treated as issues in the ready lane.

## Capability degradation

GitHub attachment upload is unsupported. Blocked-by support is capability
dependent. When native dependency support is absent, the deterministic relation
layer maintains the `flow:deps` body block and records that degradation. The
block is excluded from body-merge divergence.

All mutations validate the issue node id before writing. A moved, deleted, or
reused display number produces a structured stale/not-found/conflict result and
does not mutate local link state.
