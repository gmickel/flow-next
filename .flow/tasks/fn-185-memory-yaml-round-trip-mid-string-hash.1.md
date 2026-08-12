---
satisfies: [R1, R2, R3, R5]
---
# fn-185-memory-yaml-round-trip-mid-string-hash.1 Quote mid-string " #" scalars and make flow-list splitting quote-aware, with regression tests

## Description
In plugins/flow-next/scripts/flowctl.py: (1) extend _yaml_scalar_needs_quoting (:21009-21039) with a condition that any value containing " #" or "\t#" needs quoting (whitespace-then-hash opens a YAML comment per YAML 1.2; the existing leading-char check already covers hash-at-start). Negatives must stay unquoted: "C#/F# langs", "issue#140". (2) Extract one helper _split_flow_items(inner) that splits a flow-collection body on top-level commas while tracking double/single-quote state (with backslash escapes inside double quotes) and bracket/brace depth; wire it into the three naive split sites: the flow-list branch (:20852), the flow-mapping top-level split, and the mapping's inner-list split. (3) Add regression tests to plugins/flow-next/tests/test_memory_schema.py per spec R3 (predicate cases incl. negatives; format->safe_load round-trip guarded by skipUnless PyYAML importable; format->_parse_inline_yaml round-trip; the issue #332 two-element reproducer verbatim; a list round-trip with commas, quotes, and colon-space in items). Test-shape rules: pin contract tokens, not sentences; no prose assertions. Do NOT touch prompt constants, do NOT strip comments in the reader, do NOT add PyYAML as a dependency, do NOT run the flowctl.py propagation steps (orchestrator owns them), do NOT bump versions or edit CHANGELOG.

## Acceptance
R1 predicate true for mid-string whitespace-hash and false for C#/issue#140; R2 reproducer parses to exactly 2 verbatim elements and all three split sites share the helper; R3 tests added and green; focused suites (test_memory_schema, test_memory_marks, test_prospect_promote) green.

## Done summary
Added mid-string " #" condition to _yaml_scalar_needs_quoting (whitespace-then-hash opens a YAML comment per YAML 1.2) and extracted a quote/depth-aware _split_flow_items helper wired into all three flow-split sites in _parse_inline_yaml. 8 regression tests incl. the issue #332 reproducer and a conforming-parser (PyYAML) round-trip. Focused suites green (134 tests), ruff clean.
## Evidence
- Commits: 3eb07312
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_memory_schema test_memory_marks test_prospect_promote -q
- PRs: