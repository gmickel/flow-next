# Memory YAML round-trip: quote mid-string " #", quote-aware flow-list split (#332)

## Goal & Context

`flowctl memory add --update` re-serialises the whole frontmatter, and two round-trip holes let a value come back different from the one that went in, silently (issue #332, reported by @sn-furali, verified against main at 3.28.0):

- **(a) Writer gap.** `_yaml_scalar_needs_quoting` (flowctl.py:21009-21039) blacklists a *leading* `#` (`text[0] in "#'\"&*!|>%@`" at :21035-21036) but never checks for a `#` preceded by whitespace. Per YAML 1.2 §6.6/§7.3.3, ` #` mid-scalar opens a comment: a title stored unquoted as `landed in #140` is read by any conforming parser (PyYAML, ruby-yaml, editors) as `landed in`. flowctl's own fallback parser does not strip comments, so flowctl reads its own broken output back intact — the corruption is invisible until a conforming parser shows up. One live casualty exists in this repo: `.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md` (title truncates to "set-tracker-id rejected GitHub").
- **(b) Reader gap.** The no-PyYAML fallback `_parse_inline_yaml` splits flow lists on every comma (`inner.split(",")` at :20852), quote-blind. A 2-element list whose first element contains a comma parses as 3 mangled elements, and `--update` then writes the mis-parse back via `write_memory_entry`, producing genuinely malformed YAML (an orphaned-quote element). The same naive split exists in the flow-mapping branch (top-level split is depth-aware but not quote-aware, and its inner-list split is naive).

History: #235 recorded leading `#` as handled (it tested leading position only); #236 hardened the same function for leading `'`/`"`/`- ` and taught the fallback to unescape quoted scalars. Neither touched mid-string `#` or the comma split. Existing test surface lives in `tests/test_memory_schema.py` (TestInlineYAMLParser :172-219, TestYamlScalarNeedsQuoting :490-508, TestInlineParserRoundTrip :511-536).

Out of scope, deliberately: a `raw_frontmatter=` preservation mode for `write_memory_entry` (the reporter's structural option 3) — separate spec if wanted; and teaching `_parse_inline_yaml` to strip trailing comments (it would convert latent damage into active read-truncation for users with unquoted ` #` already on disk).

## Acceptance Criteria

- R1: `_yaml_scalar_needs_quoting` returns True for any value containing `" #"` or `"\t#"` (whitespace-then-hash opens a YAML comment). Values with non-comment hashes stay unquoted: `C#/F# langs`, `issue#140` remain False; existing True/False cases unchanged. The shared gate means `_format_yaml_list_item` inherits the fix.
- R2: flow-list splitting in `_parse_inline_yaml` is quote-aware and bracket-depth-aware via one shared helper (e.g. `_split_flow_items`), used by all three split sites: the list branch (:20852), the flow-mapping top-level split, and the mapping's inner-list split. The reporter's reproducer — `["Own it separately — rejected by the operator, who chose otherwise.", "Record it as a dep — rejected: it would misstate a priority."]` — parses to exactly 2 elements, both verbatim. Backslash escapes inside double-quoted items do not terminate the item.
- R3: regression tests in `tests/test_memory_schema.py`: (i) the R1 predicate cases incl. negatives; (ii) a `_format_yaml_value` → conforming-parser round-trip asserting a `" #"` value survives (use `yaml.safe_load` guarded by `unittest.skipUnless(yaml is importable)`, since the fallback parser cannot see the bug); (iii) a `_format_yaml_value` → `_parse_inline_yaml` round-trip for the R1 value (now quoted, the fallback also survives it); (iv) the reporter's 2-element list → len 2, elements verbatim; (v) a round-trip for a list whose items contain commas, quotes, and `": "`.
- R4: the one damaged entry in this repo, `.flow/memory/bug/integration/set-tracker-id-rejected-github-n-2026-06-03.md`, has its `title:` value quoted so a conforming parser reads the full text. No other frontmatter edits to that file.
- R5: no behavior change for any currently-correct value: rendering the full set of this repo's 93 memory entries through the new writer changes exactly one value's rendering (the R4 file's title, once repaired it is stable). Existing suites `test_memory_schema`, `test_memory_marks`, `test_prospect_promote` stay green (the `_parse_inline_yaml` callers in strategy-doc, prospect, and satisfies parsing keep their contracts).

## Boundaries

- Do NOT touch prompt text or any `*_FALLBACK` prompt constant (test_prompt_text_pinned).
- Do NOT teach `_parse_inline_yaml` to strip comments (see out-of-scope rationale).
- Do NOT add PyYAML as a dependency; it stays optional.
- Propagation gate on flowctl.py changes applies (cp to .flow/bin/flowctl.py, rsync flowctl_tracker, gen_tracker_manifest.py, sync-codex.sh twice) — run at the final gate, owned by the orchestrator close-out.
- No version bump in implementation commits; CHANGELOG entry goes under `## Unreleased`, credit @sn-furali.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_memory_schema test_memory_marks test_prospect_promote -q
```
