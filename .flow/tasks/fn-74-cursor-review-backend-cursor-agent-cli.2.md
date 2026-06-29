---
satisfies: [R5, R6, R7, R8, R11, R14]
---

## Description

Wire `cursor` into the five review commands, on top of the foundation from task .1. Add the `impl-review` / `plan-review` / `completion-review` / `validate` / `deep-pass` subcommands + `cmd_cursor_*` handlers (mirroring `cmd_copilot_*`), the `elif backend == "cursor"` branches in the shared validator/deep dispatchers, and **own-mode** `mode: "cursor"` receipts — NOT a copilot clone: each receipt mode-guard must accept `cursor`, and session resume must fire only when the prior receipt's `mode == "cursor"`. This task owns the **clean-tree integration check (R8)** because only a real review (not .1's mocked unit tests) can prove it.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (+ handler/dispatch tests, + an optional live integration test)

## Approach

- Add 5 subcommands to the cursor subparser (mirror the copilot block): `impl-review`, `plan-review`, `completion-review`, `validate`, `deep-pass`. **Only these six (with `check` from .1)** — NOT `classify-result`/`rollback-plan` (codex-only).
- Add `cmd_cursor_impl_review` / `_plan_review` / `_completion_review`, routing validate + deep-pass through the shared dispatchers via new `elif backend == "cursor"` branches.
- Receipts: `mode: "cursor"`, `spec: "cursor:<model>"`, `model: <model>`, **no `effort` key**. Carry copilot's rigor field set — confidence/classification rubric injection, suppressed-count, introduced-vs-pre_existing, unaddressed-R-ID, protected-path filtering (R14).
- The three review handlers' `mode == "copilot"` receipt guards are **cross-backend confusion checks** — give cursor its own-mode acceptance (resume only when prior receipt `mode == "cursor"`; cross-backend receipt ⇒ fresh session) (R7).
- **R8 clean-tree:** add an **optional live integration test** gated on `cursor-agent` availability — run a real `cursor impl-review` against a temp git repo and assert `git status` is identical before/after; skip cleanly when the CLI is absent (never a mocked clean-tree claim). The `--mode ask` flag (asserted in .1) is what guarantees it.
- **Do NOT add cursor to the triage LLM judge** (`--backend choices=["codex","copilot"]`) — per spec §8 it stays codex|copilot; cursor reviews use the deterministic whitelist by default.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:25950-26062` — copilot subparser subcommands (impl/plan/completion/validate/deep-pass) — the template
- `plugins/flow-next/scripts/flowctl.py:22372`,`:22603`,`:22778`,`:19308`,`:19978` — `cmd_copilot_impl_review` / `_plan_review` / `_completion_review` / `_validate` / `_deep_pass`
- `plugins/flow-next/scripts/flowctl.py:19212`,`:19233` — validator-pass `backend == codex`/`copilot` dispatch (add `cursor`)
- `plugins/flow-next/scripts/flowctl.py:19869`,`:19890` — deep-pass dispatch (add `cursor`)
- `plugins/flow-next/scripts/flowctl.py:22481`,`:22687`,`:22870` — receipt `mode == "copilot"` guards (own-mode pattern)
- `run_cursor_exec` from task .1

## Key context

Session-resume pitfall (memory `drop-receipt-to-break-codex`): a stuck/hallucinated review must be re-invokable fresh by dropping the receipt — the `mode == "cursor"` resume guard is what enables that. Resume is resume-only (cursor generates the id; never fabricate a first-call `--resume`).

## Acceptance

- [ ] `flowctl cursor impl-review <task> --base <b> --receipt <r>` writes a `mode:"cursor"` receipt (no `effort` key) and prints `VERDICT=...` (R5)
- [ ] `cursor plan-review` / `completion-review` / `validate` / `deep-pass` dispatch through `run_cursor_exec` and write the same additive receipt shapes as codex/copilot (`mode:"cursor"`) (R6)
- [ ] re-review resumes via `--resume <session_id>` only when the prior receipt's `mode == "cursor"`; a cross-backend receipt starts a fresh session (R7)
- [ ] optional live integration test (gated on `cursor-agent` present) runs a real `cursor impl-review` against a temp git repo and asserts `git status` unchanged; skipped when the CLI is absent (R8)
- [ ] cursor `impl-review` / `completion-review` receipts carry copilot's rigor fields (confidence anchors, suppressed counts, introduced-vs-pre_existing, unaddressed R-ID, protected-path); a parity test asserts those fields AND that `effort` is absent (R14)
- [ ] handler + dispatch tests pass; triage `--backend` choices unchanged (`codex|copilot`); full suite green (R11)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
