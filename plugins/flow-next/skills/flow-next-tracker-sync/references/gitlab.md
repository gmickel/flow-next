# GitLab tracker transport shape

Flowctl uses authenticated GitLab CLI transport with REST-token fallback inside
the deterministic executor. Self-managed host, protocol, port, namespace, and
project id come from the resolved destination. Skill prose never builds GitLab
requests.

## Addressing

- destination: resolved project id and path;
- durable issue identity: global issue id;
- display identity: `project#iid`;
- parent verification: issue id on the parent read;
- note response parent identity: `noteable_id`.

## Operation mapping

| Normalized operation | GitLab shape |
|---|---|
| issue read/update | project issue by IID |
| comments | issue notes, excluding system notes |
| labels | issue label names |
| assignees | user ids |
| status | open/closed state plus configured labels |
| list-open | project issues filtered by configured ready label |
| relation | issue link when tier permits, with flow-owned body provenance |
| attachment | project upload followed by Markdown link |

Issue descriptions and notes normalize as Markdown. Pagination is completed
inside flowctl. The adapter preserves self-managed host selection without
placing credentials in argv.

## Capability degradation

GitLab tier controls directional blocked-by relations. If the licensed
directional shape is rejected, flowctl records the capability transition and
uses the documented lower-fidelity relation plus the `flow:deps` body block.
That block remains the durable direction/provenance source and is excluded from
body divergence.

Upload metadata is capability-supported. Download follows the returned project
upload path and safe-output rules.
