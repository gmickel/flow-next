---
satisfies: [R2, R4]
---
# fn-138-published-json-schema-for-flow-config.2 Reader-schema drift test + fixture validation

## Description
Both-directions honesty between the config reader and the schema; fixture validation.

**Size:** M

### Approach
- Drift test - the canonical key-set is defined as THREE parts (call-site grep is NOT the primary mechanism; `config get` accepts any dotted key so call sites are both noisy and incomplete): (a) dotted leaves of `get_default_config()` (mechanical backbone - covers land/work/pipeline/pilot/artifacts/tracker settings), (b) an explicit ANNOTATED allowlist for keys OUTSIDE the defaults tree: machine-written blocks (`tracker.resolved.*` via the resolve transaction, `tracker.provenance`, `tracker.perTracker.*`), pattern families, and `$schema` itself - NOTE `review.backend`, `tracker.specIds`, `tracker.conflictTiebreak`, and `models.*` all HAVE default leaves and live in (a); the comparator uses (a) UNION (b) and never assumes disjointness, (c) a guard that greps flowctl-side `get_config`/tree-probe string literals and FAILS on any literal not accounted for by (a)+(b). Assert schema-keys == (a)+(b) both directions. Inventory boundary is flowctl-side ONLY - skills read arbitrary subtrees via jq (e.g. land's lcfg()); they are consumers of the same key-set, never a second inventory.
- Fixture configs valid + invalid (bad enum, bad spec-grammar, unknown-key behavior documented per the additionalProperties policy in the spec) validated with a small stdlib structural checker (no new deps).
- The single best anti-regression fixture: a freshly-scaffolded config (setup's _init_persisted_defaults shape + stamped $schema) MUST validate against the committed schema.

## Acceptance
- [ ] Drift test fails on either-direction divergence (R2).
- [ ] Fixture validation stdlib-only (R4).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
