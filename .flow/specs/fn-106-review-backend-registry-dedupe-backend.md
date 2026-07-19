# fn-106 review backend registry: dedupe backend clones, prompts to templates

> STUB from the fn-101 audit (2026-07-19). The extensibility spec: adding review backend #4 must become a registry entry, not a 4th copy of everything. Interview/plan before building.

## Goal & Context

The review family is ~11.4k LOC (34% of flowctl.py). The 9 review commands (codex/copilot/cursor x impl/plan/completion) are near-clones totaling 2,314 LOC (difflib similarity 0.47-0.75) with byte-identical git-diff gathering blocks at flowctl.py:24195/25216/25923/26403; supporting triplets (resolve-spec, check, validate, deep-pass, version probes) add ~700 more. `BACKEND_REGISTRY` (flowctl.py:4020) already exists half-built (models, efforts, defaults) and `_dispatch_review_with_fallback` already takes callables.

## Approach

1. Extend BACKEND_REGISTRY with run_exec / resolve_spec / check_probe / prompt-fit hooks; one `cmd_backend_review(backend, kind)` driver replaces the 9 clones. Genuine variance stays as hooks: cursor argv budget (4788-4929), copilot session marker (4551), codex sandbox (3158). Estimated -1,800 to -2,100 LOC; argparse blocks collapse to parameterized registration.
2. Move ~780 LOC of embedded f-string review prompts (flowctl.py:5133-5421, 5586-5804, 21354-21503, 24724-24877) to skill .md templates using the existing `load_validator_template`/`load_deep_pass_template` loader + embedded-fallback pattern. Prompts become visible prose the sync script rewrites.
3. Tighten the reviewer output contract: backends emit a fenced JSON block for tallies/findings; `parse_suppressed_count`/`parse_classification_counts`/`parse_unaddressed_rids`/`parse_deep_findings` (~560 LOC of tolerant prose regex) shrink to json.loads + schema check. Verdict tag contract (<verdict>SHIP</verdict>) is UNCHANGED - it is the sanctioned edge.
4. Fold `cmd_cursor_validate`/`cmd_cursor_deep_pass`/377-line `cmd_cursor_completion_review` into the shared pipeline like codex/copilot.
5. Deep-pass confidence-promotion and verdict-recompute math: see fn-107 for the judgment question; this spec only relocates/dedupes, fn-107 decides what survives.

## Acceptance

- 9 cmd_*_review clones replaced by 1 driver + registry entries; net LOC reduction >= 1,500 in flowctl.py.
- All existing review receipts byte-compatible (schema unchanged) - pilot/ralph/land readers unaffected.
- test_backend_spec.py (140), test_cursor_review_commands.py, review smokes green unchanged.
- Adding a hypothetical 4th backend demonstrated in a test using only a registry entry.

## Boundaries

- No new backends in this spec. No receipt-schema changes. RALPH_ITERATION stamping dedupe belongs to fn-108 (coordinate; whoever lands first extracts the helper).
