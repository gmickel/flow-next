---
satisfies: [R8, R13]
---

# Docs + CHANGELOG + smoke prose contracts + final Codex mirror regen

## Description

Size: M
Files:
- `plugins/flow-next/docs/tracker-sync.md` (dispatch-mode section + Foreground paragraph)
- `plugins/flow-next/docs/ralph.md` (Foreground-rule reconciliation note)
- `CHANGELOG.md` (`## Unreleased`)
- `~/work/flow-next.dev` docs-site changelog (`## Unreleased`) + navigation if a new page is warranted
- `plugins/flow-next/scripts/smoke_test.sh` (tracker-dispatch prose contracts — greenfield)
- Regenerate `plugins/flow-next/codex/` (final)

Document the async dispatch model end-to-end, add the smoke prose contracts (none exist today — greenfield), stage the CHANGELOG under `## Unreleased`, and do the final Codex mirror regen so the whole feature ships coherent.

## Approach

1. **tracker-sync.md dispatch-mode section (R8).** Add a section under "Lifecycle sync points" (:101) explaining `tracker.dispatch` (`async` default | `inline`), the fire-and-forget vs isolated-but-awaited vs state-shaped classes, per-spec state-shaped serialization, the pre-audit join, and the v1 Claude-Code-only async gate (Codex/Copilot/Droid inline). Cross-link the config leaf.
2. **Foreground-rule paragraph (R13).** Add the reconciliation paragraph (from the spec's "Foreground rule reconciliation" section) to `docs/ralph.md` — near the existing autonomous-touchpoint prose (ralph.md:607 tracker-sync note / the artifact-generate discipline at :611): host-level background `Task` dispatch (harness re-invokes the host on completion) is DISTINCT from `Bash run_in_background` in subagent contexts (fn-78); runners dispatched from HOST contexts only, never worker subagents.
3. **CHANGELOG (R8).** Add an entry under `## Unreleased` (repo `CHANGELOG.md`) summarizing: tracker lifecycle dispatches now run off-critical-path in a context-isolated `tracker-runner` subagent (Claude Code; Codex/Copilot/Droid inline in v1); `tracker.dispatch` opt-out hatch; no behavior change with the bridge off. Do NOT bump the version (batched-release rule) — stage under `## Unreleased` only.
4. **Docs-site (R8, downstream currency).** Mirror the CHANGELOG summary into the `~/work/flow-next.dev` docs-site changelog under its `## Unreleased`/Latest (per `agent_docs/releasing.md` "Docs-site changelog entry"); update tracker-sync page copy if it describes lifecycle sync. Gate: `cd ~/work/flow-next.dev && pnpm build`. (Committed separately in that repo.)
5. **Smoke prose contracts (R8).** In `smoke_test.sh` add tracker-dispatch prose assertions (greenfield — there are ZERO today): e.g. assert `tracker-touchpoints.md` references the tracker-runner dispatch, assert `agents/tracker-runner.md` exists with the `disallowedTools`/`model` contract, assert `tracker.dispatch` default is `async`. Model on existing smoke prose-contract patterns.
6. **Final mirror regen (R8).** Run `./scripts/sync-codex.sh`; confirm the structural guard (`Task flow-next:` = 0), `AskUserQuestion`-in-prose guard, and `test_tracker_sync_mirror_parity.py` are all green after all touchpoint edits from .1-.3 are in.
7. **Full gate.** `uvx pytest plugins/flow-next/tests -q` + `bash plugins/flow-next/scripts/smoke_test.sh` (from OUTSIDE the repo) green.

## Investigation targets

Required:
- `plugins/flow-next/docs/tracker-sync.md:101-140` (Lifecycle sync points — insertion point)
- `plugins/flow-next/docs/ralph.md:600-612` (autonomous-touchpoint prose — where the Foreground paragraph fits)
- `plugins/flow-next/scripts/smoke_test.sh` (prose-contract assertion patterns — grep for existing tracker/agent contract checks)
- `CHANGELOG.md` (`## Unreleased` section head)

Optional:
- `agent_docs/releasing.md` ("Docs-site changelog entry" workflow)
- `plugins/flow-next/tests/test_tracker_sync_mirror_parity.py` (final parity gate)

## Key context

- Docs-only changes do NOT bump the plugin version; the whole spec is staged under `## Unreleased` (batched release decided later). Do NOT run `scripts/bump.sh`.
- smoke_test.sh runs from OUTSIDE the repo (bundled-copy invariant) — the prose contracts assert against the installed plugin tree; follow the existing harness conventions.
- The docs-site (`~/work/flow-next.dev`) is a SEPARATE repo — commit there separately; the maintainer's downstream-currency requirement (repo docs → flow-next.dev → AI×SDLC → vault) is a standing chain, but this task covers only repo docs + flow-next.dev; the broader chain is a release-time walk.
- This is the LAST task in the chain — it must run after all touchpoint edits so the final mirror regen + full gate reflect the complete feature.

## Acceptance

- [ ] `docs/tracker-sync.md` has a dispatch-mode section (classes, serialization, pre-audit join, v1 Claude-only async gate) + cross-link to the config leaf.
- [ ] `docs/ralph.md` carries the Foreground-rule reconciliation paragraph (host `Task` background vs subagent `Bash run_in_background`; host-only dispatch).
- [ ] `CHANGELOG.md` has an `## Unreleased` entry; NO version bump.
- [ ] `~/work/flow-next.dev` docs-site changelog updated under Unreleased/Latest; `pnpm build` green (committed separately).
- [ ] `smoke_test.sh` carries tracker-dispatch prose contracts (runner dispatch reference, `agents/tracker-runner.md` contract, `tracker.dispatch` default).
- [ ] Final `./scripts/sync-codex.sh` regen: structural guard + AskUserQuestion guard + `test_tracker_sync_mirror_parity.py` green.
- [ ] `uvx pytest plugins/flow-next/tests -q` + `bash plugins/flow-next/scripts/smoke_test.sh` (from outside the repo) both green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
