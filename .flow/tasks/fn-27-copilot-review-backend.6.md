## Description

Setup-skill detection of `copilot` CLI + smoke test coverage for the copilot backend. These two live together because both touch test-setup surfaces.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md`
- `plugins/flow-next/scripts/smoke_test.sh`

## Approach

**flow-next-setup/workflow.md:**
- `workflow.md:150-349` — the tool detection block and question-building block. Add `which copilot` detection alongside existing `which rp` / `which codex`. Extend the question text to include Copilot CLI as an option.
- Line 342-349 (answer → backend mapping): add `"Copilot"*|"copilot"*) REVIEW_BACKEND="copilot" ;;` alongside the codex / rp branches.

**smoke_test.sh:**
- **Copilot commands section** — mirror `smoke_test.sh:476-512` ("codex commands" block). Add equivalent for copilot:
  - `flowctl copilot check --help`
  - `flowctl copilot impl-review --help`
  - `flowctl copilot plan-review --help`
  - `flowctl copilot completion-review --help`
- **Copilot e2e section** — mirror `smoke_test.sh:697-799` ("codex e2e" block). Insert after codex block. Guard with `if command -v copilot >/dev/null` to skip when copilot CLI not installed:
  - Create test epic + task
  - Run `flowctl copilot plan-review <epic> --files=<sample.md> --receipt <tmp-path>` against a trivial sample
  - Assert receipt has expected keys: `type, id, mode, verdict, session_id, model, effort, timestamp, review`
  - Assert `mode == "copilot"`
  - Clean up: epic reset, receipt unlink

Use `gpt-5-mini` + `--effort low` for the e2e to minimize premium-request cost and wall time.

**Model caveat from task 1**: Claude-family models (e.g., `claude-haiku-4.5`) reject `--effort` with `Error: Model ... does not support reasoning effort configuration`. Since `run_copilot_exec` always passes `--effort`, the e2e must use a GPT model that accepts effort. `gpt-5-mini` is the cheapest viable choice.
<!-- Updated by plan-sync: task 1 discovered claude-haiku-4.5 rejects --effort; e2e must use gpt-5-mini -->

**Auth-failure test caveat from task 2**: `COPILOT_GITHUB_TOKEN=bogus flowctl copilot check` does NOT force an auth failure in copilot CLI 1.0.34 — the CLI uses its own credential store and ignores env-var overrides. To cover the `authed: false` branch of `cmd_copilot_check` (and any equivalent failure paths added to review commands), write a **mocked subprocess test** rather than relying on a live env override. (Task 2 acceptance item 4 was satisfied via the exit-path docstring + skip-probe check; smoke_test.sh should follow the same pattern or skip the failure branch entirely.)
<!-- Updated by plan-sync: task 2 worker found env-var override doesn't force auth failure; use mocked subprocess for the authed:false branch -->


## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:150-349` — detection + question block
- `plugins/flow-next/scripts/smoke_test.sh:476-512` — codex commands section
- `plugins/flow-next/scripts/smoke_test.sh:697-799` — codex e2e section

**Optional:**
- `plugins/flow-next/scripts/ralph_smoke_test.sh` — for reference only (no existing codex coverage per repo-scout; adding copilot here is optional)

## Acceptance

- [ ] `flow-next-setup` skill detects `copilot` on PATH and includes it in the backend-selection question
- [ ] Answering with "copilot" writes `review.backend=copilot` to `.flow/config.json`
- [ ] `smoke_test.sh` runs copilot command help checks in parallel with codex
- [ ] `smoke_test.sh` copilot e2e runs against live copilot CLI when installed; skips cleanly otherwise
- [ ] E2e asserts receipt schema includes `model` and `effort` fields (new vs codex)
- [ ] E2e uses `gpt-5-mini` + `--effort low` to stay cheap/fast (claude-haiku-4.5 rejects `--effort`; see task-1 caveat)
- [ ] Full `smoke_test.sh` still passes with no copilot installed (skipped path)

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
