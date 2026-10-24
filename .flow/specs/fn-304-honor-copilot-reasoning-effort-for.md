# Copilot reasoning effort and review diff transport

## Problem

`run_copilot_exec` previously omitted reasoning effort for Claude-family models and sent OpenAI-family models the `--effort` option. The installed GitHub Copilot CLI 1.0.98 help exposes `--reasoning-effort` with `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`, so the resolved effort must use that option.

Copilot review sessions also deny shell access while the shared review prompts ask reviewers to inspect the Git diff. In review run `RID6e3c4750889e48ffa25228bb5eb678dc` over `627efd03862b663482ec34a66d7559f482a14529..b5d103c1bddec7c114926108c5795ee29adb3799`, all three sessions returned `SHIP` after auditing current files without reading the patch. That recorded verdict has no diff coverage and is incomplete. Copilot primary reviews and fanout draws need the exact pinned diff at a readable path and instructions to use the available read-only file tools while shell remains denied. Preserve the existing Claude transport behavior.

## Acceptance criteria

- **R1:** For Claude-family and OpenAI-family models, dispatch the resolved effort, including `high`, using the CLI-supported `--reasoning-effort` option.
- **R2:** At the model-resolution floor, omit `--reasoning-effort` and keep the receipt truthful about the effective model and effort.
- **R3:** Preserve read-only tool restrictions, POSIX and Windows prompt delivery, first-call and resumed session behavior, model-unavailable fallback classification, and accurate receipts for non-floor dispatches.
- **R4:** For Copilot primary implementation, plan, and completion reviews, plus each implementation fanout draw, materialize the exact pinned base-to-head diff before managed or CLI dispatch and tell the reviewer to read it with the available read-only file tools because shell access is denied. Keep receipt and range identity in the diff filename, fail before dispatch when materialization fails, and preserve Claude diff delivery behavior.
