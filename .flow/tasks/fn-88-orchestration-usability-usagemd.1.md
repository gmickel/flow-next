---
satisfies: [R1, R14]
---

## Description

Add the `## Orchestration & model steering` section to the setup skill's usage.md template, and mirror it byte-identically into the repo-root dogfood copy.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-setup/templates/usage.md`, `.flow/usage.md` (dogfood mirror, same commit), `plugins/flow-next/codex/**` (regenerated)

## Approach

- Insert after `## Config`, before `## Checkpoint` (per docs-gap-scout: ~L164-176 of the template).
- Content per spec R1 — agentic headless-bridge instructions written for the host agent to execute, ≤ ~60 lines:
  - `codex exec` recipe: read-only default sandbox called out; `--sandbox workspace-write` for implementation (`--full-auto` deprecated); `-o/--output-last-message` for result capture; `</dev/null` stdin guard (hang bug when spawned by another agent); `-s read-only` investigation mode; self-contained-prompt discipline (context in, digest back, never touches git); no recursive delegation.
  - `cursor-agent` recipe: `-p` print mode, `--force` to apply edits, `CURSOR_API_KEY` for headless auth, model IDs volatile → `--list-models`.
  - Harness-relative wording (from Claude Code the bridges are codex exec/cursor-agent; from Codex, `claude -p`/cursor-agent).
  - flow-next shortcuts: `delegate:codex` quickstart, `review.backend` one-liners + per-task `review:` example.
  - 2–3 prompted-orchestration examples (per-item complexity routing; conditional escalation) — reuse the phrasing from `docs/orchestration.md` "Prompted orchestration" section, compressed.
  - Links: `docs/orchestration.md` + `https://flow-next.dev/orchestration/`.
- Source material: `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `docs/orchestration.md`, `docs/flowctl.md` review-backend section. CLI facts are already verified (scout pass 2026-07-05) — do not soften them.
- Regenerate the Codex mirror: `./scripts/sync-codex.sh` (templates copy wholesale; catch-all prose rewrites apply).

## Investigation targets

**Required** (read before writing):
- `plugins/flow-next/skills/flow-next-setup/templates/usage.md` — insertion point + house style
- `plugins/flow-next/docs/orchestration.md` — source content to compress (never re-embed wholesale)
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` — delegate:codex facts
- `plugins/flow-next/tests/test_dogfood_template_parity.py:36-45` — the parity pair that must stay green

**Optional:**
- `plugins/flow-next/docs/flowctl.md:649-700` — review-backend grammar + precedence

## Key context

- `test_dogfood_template_parity.py` asserts `.flow/usage.md` ≡ `templates/usage.md` byte-for-byte — update BOTH in the same commit or CI fails (R14).
- usage.md is installed into every project and read often — budget is a hard constraint, link don't embed.

## Acceptance

- [ ] Section present in template, ≤ ~60 lines, all R1 recipe elements included (sandbox default, `-o` capture, stdin guard, `--force`, `CURSOR_API_KEY`, volatile-IDs note, delegate/review shortcuts, ≥2 prompted examples, both links)
- [ ] `.flow/usage.md` updated byte-identically same commit; `test_dogfood_template_parity.py` green
- [ ] `./scripts/sync-codex.sh` run, validation suite green, mirror committed
- [ ] Full pytest + smoke_test.sh green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
