# Codex reviews: persona override, project-doc suppression, plan-prompt role anchor, honest no-verdict class (#331)

## Goal & Context

Issue #331 (@sn-furali): `flowctl codex plan-review` returned no verdict 13 consecutive times. Two independent instruction-contamination channels reach the codex reviewer subprocess, and flow-next's only counter-instruction is gated behind a flag codex never opted into. Verified against main:

- **Route A** - `codex exec` auto-loads the host repo's `AGENTS.md`. In a repo whose AGENTS.md directs agents to drive reviews through the flow-next skills, the reviewer adopts that role and re-dispatches `flowctl codex plan-review` at itself; the codex safety layer rejects the nested dispatch and the turn ends verdict-less. Reporter measured `-c project_doc_max_bytes=0` fixes this route.
- **Route B** - with the flow-next codex plugin installed, the reviewer reads the plugin's own coordinator skills (`codex/skills/flow-next-{plan-review,impl-review,spec-completion-review}/SKILL.md`: "Role: ... Coordinator (NOT the reviewer)", "never self-declares a verdict"), adopts the coordinator role, completes a good review, and withholds the verdict tag. Self-inflicted: our text reaching the one process that must declare a verdict.
- **Key finding**: codex's `needs_persona_override: False` (BACKEND_REGISTRY, flowctl.py ~:41820) was never a decision - it mechanically preserved pre-existing behavior when #296 extracted the registry. The persona preamble (`build_cursor_persona_override`, ~:12210) already names both routes verbatim ("auto-attached workspace AGENTS.md / CLAUDE.md, skill catalogs, or MCP instruction blocks ... superseded") and closes with the verdict-grammar instruction. The plumbing is backend-agnostic (plain user-prompt prepend; codex delivery is stdin with `prompt_fit: "none"` so no fit cost). Only the name, docstring, and docs/orchestration.md:~128 are cursor-specific.
- **Amplifier**: `plan-review-prompt.md` is the ONLY review prompt missing the "You ARE the reviewer - review directly." anchor that impl/standalone/completion prompts gained in #246 (`git log -S "You ARE the reviewer"` -> e6a86018). Same gap in `PLAN_REVIEW_PROMPT_FALLBACK` (~:9433) vs the other three fallbacks.
- **Separable misclassification**: the failure-class ladder (~:42419-42432) tests `"timeout" in combined` BEFORE exit-code/emptiness, where `combined` includes the reviewer's own output - so a healthy exit-0 no-verdict run whose output merely contains the word "timeout" lands in `failure_class: "timeout"` instead of the existing `missing_verdict` class. Note the class is a journal label, not a control input: `outcome = "verdict" if verdict else "transport_failure"` (~:10931) drives `review_transport_failures` regardless. Full budget redesign is out of scope; what we fix is the classification order plus an honest, actionable terminal message when the consecutive-failure cap is hit by missing_verdict failures (instruction-contamination guidance, not "repair the backend/environment").

Test/pin landscape (verified): no existing test pins `needs_persona_override` values or the codex argv shape (the frozen inventory in test_review_prompt_constraints counts call sites, not argv). Cursor persona presence is pinned by test_cursor_review_commands ~:559-585. Prompt changes require updating template + fallback SHA pins in test_prompt_text_pinned.py, keeping test_review_prompt_template_parity green, and regenerating the codex mirror.

## Acceptance Criteria

- R1: `BACKEND_REGISTRY["codex"]["needs_persona_override"]` is True; the persona function is renamed `build_review_persona_override` (all call sites + the cursor test reference updated) with a per-backend docstring (cursor: no system-prompt channel; codex: project-doc auto-load + plugin skill catalogs). Persona presence on the codex path is pinned for all three review kinds (mirroring the cursor persona tests). The persona TEXT is unchanged.
- R2: both codex exec argv paths - fresh dispatch (~:4707-4718) AND resume (~:4651-4656) - carry `-c project_doc_max_bytes=0`; an argv-shape regression test pins the flag on both paths.
- R3: `plan-review-prompt.md` and `PLAN_REVIEW_PROMPT_FALLBACK` open with the same "You ARE the reviewer - review directly." anchor paragraph the other three prompts carry (byte-identical parity template<->fallback preserved); SHA pins in test_prompt_text_pinned.py updated in the same commit with the rationale in the commit message.
- R4: classification order fixed so an exit-0, non-empty, no-verdict run classes as `missing_verdict` even when the output contains the word "timeout" (scope the timeout substring scan to stderr, or order exit-code/emptiness checks first - implementer judgment, pinned by a regression test); both ladders (review path ~:42419 and rp path ~:30451) get the same fix.
- R5: when the consecutive-failure cap terminates the dispatch and the recorded failures are missing_verdict-class, the terminal message names the likely cause (reviewer inherited host/plugin instructions and declared no verdict) and the remedies (persona override now default; check AGENTS.md size / plugin skill exposure) instead of the generic `TRANSPORT_UNHEALTHY ... repair the backend/environment`. Transport-class failures keep the existing message. The bounded-retry cap semantics are unchanged.
- R6: docs/orchestration.md's cursor-only persona framing (~:128, incl. "There is no CLI knob to suppress the auto-attach") is rewritten per-backend; CHANGELOG under `## Unreleased` credits @sn-furali.

## Boundaries

- Do NOT change the persona text (it is a Python constant, deliberately shared).
- Do NOT reach for `--ignore-user-config`/`--ephemeral` (drops user model providers/MCP config as collateral); route B is covered by R1's persona precedence.
- Do NOT redesign the transport-failure budget/counter (product decision deferred); R4/R5 are classification + message honesty only.
- Do NOT edit the codex-mirror coordinator SKILL.md files by hand - the mirror is generated; if scoping "never self-declares" to the coordinator role is wanted later, it belongs in the canonical skills, a separate change.
- flowctl.py propagation gate at close-out (orchestrator-owned): cp to .flow/bin, tracker manifest, sync-codex twice.
- No version bump in implementation commits.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_backend_spec test_cursor_review_commands test_prompt_text_pinned test_review_prompt_constraints -q
```
