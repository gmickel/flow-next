---
satisfies: [R1, R2]
---
# fn-187-codex-reviews-persona-override-project.1 Flip codex persona override on; rename the persona builder; suppress project docs in codex review argv; tests

## Description
In plugins/flow-next/scripts/flowctl.py: (1) R1 - set BACKEND_REGISTRY['codex']['needs_persona_override'] = True (~:41820). Rename build_cursor_persona_override -> build_review_persona_override (def ~:12210 + the three call sites ~:42128/:42593/:42873 + any other refs; grep). Rewrite the docstring per-backend: cursor has no system-prompt channel; codex auto-loads host project docs (AGENTS.md) and plugin skill catalogs into the reviewer subprocess. Do NOT change the returned persona TEXT (byte-identical). (2) R2 - add '-c', 'project_doc_max_bytes=0' to BOTH codex exec argv paths: fresh dispatch in run_codex_exec._dispatch (~:4707-4718) AND the resume path (~:4651-4656). (3) Tests: update test_cursor_review_commands.py references to the renamed function (its persona-presence pins must stay green); add codex-path persona-presence tests for all three review kinds mirroring the cursor ones (~:559-585 pattern); add an argv-shape test pinning project_doc_max_bytes=0 on both fresh and resume codex argv. Run the Quick-commands suites plus test_cursor_review_commands and any codex-dispatch suites you touch. Do NOT touch prompt templates or *_FALLBACK constants (task 2 owns R3), do NOT touch the failure-class ladders (task 3 owns R4/R5).

## Acceptance
R1+R2 met; persona byte-identical; no existing assertion broken; new pins green; uvx ruff@0.16.0 check clean on touched files.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
