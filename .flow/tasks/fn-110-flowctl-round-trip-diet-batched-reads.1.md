---
satisfies: [R1, R2, R7]
---

## Description

The flowctl half: subtree `config get` + create-time task section files. Pure plumbing, zero behavior change to existing calls.

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py (byte-identical, same commit), plugins/flow-next/tests/test_config_subtree.py (new), plugins/flow-next/tests/test_task_create_files.py (new)

## Approach

- Subtree read in `cmd_config_get` (flowctl.py:7243): when the resolved key maps to a dict in the merged config, return `{"key": <prefix>, "value": {<subtree>}}`; scalars byte-identical to today. `--raw` parity: subtree of set-only values (absent leaves omitted, not defaulted). ONE config.json parse per invocation; reuse `resolve_config_key_for_read` (:1466) per leaf - do not fork a resolver (fn-111 deletes the alias machinery next door).
- `task create` (:13712) gains `--description-file/--acceptance-file`: reuse `task set-spec`'s section-writing helpers (:17355 area) so normalization + H2-layering (fn-79) are identical; error cleanly on unreadable file; flags optional and independent.

## Investigation targets

**Required:**
- flowctl.py:7243 cmd_config_get + :1466 resolver (current merged/raw split)
- flowctl.py:13712 cmd_task_create + the set-spec helpers it will reuse
- tests/test_config_alias.py + test_land_config.py (existing config-test shapes to extend, one file per domain convention)

## Key context

- Memory skill-prose-must-match-real-flowctl-2026-06-10: verify emitted JSON keys before writing skill prose against them (fn-110.2 depends on the exact shape you ship here).
- fn-111 coordination: your subtree code should sit cleanly beside (not inside) the alias resolvers so their deletion rebases trivially.

## Acceptance

- [ ] Subtree/scalar/raw/missing-key/alias-seam unit tests green; scalar output byte-identical to 2.20.0 on the existing test corpus (R1)
- [ ] task create with both/either/neither file flags tested incl. malformed file error; created sections identical to an equivalent create+set-spec (R2)
- [ ] One config parse per invocation (count test via monkeypatched open or parse-counter)
- [ ] Dual-copy cmp clean; full unittest + smoke (temp dir) green (R7)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
