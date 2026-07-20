---
satisfies: [R1, R2, R7]
---

## Description

The flowctl half: snapshot-based `config get` (root + subtree reads) and create-time task completeness (`--description-file`, `--satisfies`). Zero behavior change to existing calls.

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py (byte-identical, same commit), plugins/flow-next/tests/test_config_snapshot.py (new), plugins/flow-next/tests/test_task_create_files.py (new)

## Approach

- Command-scoped config snapshot: read config.json raw AT MOST once per invocation (exactly once when it exists), derive merged once, pass into `resolve_config_key_for_read` (flowctl.py:1466) via a NEW OPTIONAL parameter (default None = current behavior for all other callers). No cache outliving the command.
- `cmd_config_get` (:7243): keyless -> root snapshot `{"key": null, "value": {<full merged>}}`; dict-valued prefix -> subtree; scalar -> byte-identical to 2.20.0. `--raw` parity for root/subtree = set-only values, absent leaves omitted. Canonical-key emission with existing alias read-warning semantics (map empty today; test via injected alias).
- `task create` (:13712): NEW `--description-file` (set-spec's description normalization, fn-79 H2-layering) + NEW `--satisfies R1,R3` via a NEW zero-dependency task-frontmatter renderer (no writer exists today - set-spec --file takes pre-rendered docs). Grammar: comma list, trimmed; empty tokens rejected; duplicates rejected; order preserved; tokens must match the canonical grammar `R[1-9][0-9]*[a-z]?` (R4a-style siblings valid; R0/uppercase/multi-letter suffixes invalid); malformed input errors BEFORE any write. Equivalence test vs create + set-spec --file with a frontmatter document (parsed by the existing reader). `--acceptance-file` ALREADY EXISTS - do not re-register; byte-compat regression test for acceptance-only invocations. All input files fully read BEFORE any write; error cases: missing file, unreadable file, directory-as-path, partial flag combos.

## Investigation targets

**Required:**
- flowctl.py:7243 cmd_config_get + :1466 resolver (merged/raw split + where get_config reparses today)
- flowctl.py:13712 cmd_task_create (current flag surface incl. the existing --acceptance-file path) + set-spec helpers (:17355 area)
- tests/test_config_alias.py + test_land_config.py (shapes to extend)

## Key context

- Reviewer round-1 findings baked in: root read required (plan/pilot span namespaces with no common prefix); resolver reuse must go through the snapshot parameter (each bare resolver call reparses today); --acceptance-file pre-exists.
- fn-111 coordination: snapshot code sits beside, not inside, the alias resolvers.
- Memory skill-prose-must-match-real-flowctl-2026-06-10: fn-110.2 writes prose against your exact JSON shapes - keep them boring and stable.

## Acceptance

- [ ] Root/subtree/scalar/raw/missing-key/alias-seam tests green; scalar output byte-identical on existing corpus; parse-count test proves at-most-one (R1)
- [ ] --description-file + --satisfies land (renderer specified above); acceptance-only back-compat regression green; satisfies grammar cases (R1/R10/R4a valid; R0, R4A, R4ab, empty token, duplicate rejected; order preserved) + equivalence-vs-set-spec test + pre-write ordering + all four file error cases tested (R2)
- [ ] Dual-copy cmp clean; full unittest + smoke (temp dir) green (R7)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
