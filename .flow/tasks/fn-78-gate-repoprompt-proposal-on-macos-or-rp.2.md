# fn-78-gate-repoprompt-proposal-on-macos-or-rp.2 Regen Codex mirror + CHANGELOG Unreleased + doc annotations for the RepoPrompt gate

## Description
TBD

## Acceptance
## Acceptance Criteria (fn-78 R7–R8)

- **R7:** All canonical edits from task .1 are propagated to the Codex mirror by running `scripts/sync-codex.sh`; the regenerated `plugins/flow-next/codex/**` is committed with NO hand-edits to the mirror. Verify the mirror's plan / plan-review skill text carries the eligibility gate.
- **R8:** No plugin version bump (per CLAUDE.md batched-release rule). Add an `## Unreleased` entry to the repo `CHANGELOG.md` describing the gate; check docs that describe rp as the "Primary / macOS backend" (`docs/platforms.md`, `docs/troubleshooting.md`, `flow-next-setup/workflow.md:471` label) and, where they imply rp is always offered, annotate that non-Mac hosts without rp-cli are not proposed it. (Docs-site changelog is a downstream/maintainer step — note it, do not block on it.)

**Files:** run `scripts/sync-codex.sh` → `plugins/flow-next/codex/**`; `CHANGELOG.md`; docs as needed.

**Depends on:** task .1 (mirror regen must run AFTER the canonical skill edits land).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
