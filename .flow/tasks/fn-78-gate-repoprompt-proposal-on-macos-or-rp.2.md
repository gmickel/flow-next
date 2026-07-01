# fn-78-gate-repoprompt-proposal-on-macos-or-rp.2 Regen Codex mirror + CHANGELOG Unreleased + doc annotations for the RepoPrompt gate

## Description

Propagate task .1's canonical skill edits to the Codex mirror (`scripts/sync-codex.sh`), add a repo `CHANGELOG.md` `## Unreleased` entry, and annotate the rp "Primary/macOS backend" docs. No version bump (batched-release convention). Does NOT edit `flow-next-setup` (out of scope). Depends on task .1.

## Acceptance

- **R7:** Task .1's canonical edits are propagated to the Codex mirror by running `scripts/sync-codex.sh`; the regenerated `plugins/flow-next/codex/**` is committed with NO hand-edits to the mirror. The mirror's plan / plan-review skill text carries the eligibility gate.
- **R8:** No plugin version bump (CLAUDE.md batched-release rule). A repo `CHANGELOG.md` `## Unreleased` entry describing the gate is **required**. The **docs-site changelog is a downstream maintainer step — noted, NOT a blocking acceptance here.** Check docs describing rp as the "Primary / macOS backend" (`docs/platforms.md`, `docs/troubleshooting.md`) and, where they imply rp is always offered, annotate that non-Mac hosts without rp-cli are not proposed it. **Do NOT edit `flow-next-setup`** (out of scope per spec Boundaries — its `HAVE_RP` label is already correct; read-only reference only).
- **R9 (c, d — this task's slice):** Run `scripts/sync-codex.sh`, then confirm canonical↔mirror parity with `git diff --exit-code plugins/flow-next/codex/` clean after a second (idempotent) regen — no drift, no hand-edits. Run the repo's existing skill/mirror smoke check green (the sync-codex verification CI runs).

**Files:** run `scripts/sync-codex.sh` → `plugins/flow-next/codex/**`; `CHANGELOG.md`; `docs/platforms.md`, `docs/troubleshooting.md` as needed. NOT `flow-next-setup`. NOT a version bump.

## Done summary
Regenerated the Codex mirror via scripts/sync-codex.sh so the fn-78.1 RP_ELIGIBLE gate lands in the mirror's plan/plan-review skills (no hand-edits, byte-identical on second regen), added the required CHANGELOG.md ## Unreleased entry (no version bump), and annotated docs/platforms.md (new "RepoPrompt review backend (macOS-only)" section) + docs/troubleshooting.md that non-Mac hosts without rp-cli are not proposed the rp path — with per-skill accurate backend lists after cursor review feedback.
## Evidence
- Commits: d486ba2c33072a21f859513526feb498333fc791, 6111f02e17c923c594d17aecd52f320f9dd36573
- Tests: ./scripts/sync-codex.sh (built-in verification all green), idempotency: md5 of codex/** identical across two regens, git diff --exit-code plugins/flow-next/codex/ after post-commit regen (clean), flowctl cursor impl-review --base 6c0fc024 (verdict SHIP after 1 fix round)
- PRs: