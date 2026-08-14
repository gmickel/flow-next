# fn-197-copy-less-installs-resolve-flowctl-from.6 Downstream sweep and release notes

## Description
**What:** Downstream sweep + release notes — walk the whole chain per `~/work/agent-instructions/downstream-properties.md`.

**Details:**
- Read `~/work/agent-instructions/downstream-properties.md` first and walk every property it lists. Known targets:
  - **flow-next.dev**: install + setup + platforms pages — the copy-mode story comes out everywhere; setup page states the install-once / setup-once-per-repo / re-run-only-on-snippet-bump model; migration note (delete old `.flow/bin`, `.flow/templates/spec.md`, `.flow/usage.md`).
  - **Microsite + AI x SDLC guide**: any setup/install references updated to the one-mode story.
  - **Vault** (`~/work/GordonsVault`): update flow-next operational notes touching setup/copies.
- Release-notes draft for the batched release this rides in (candidate: the flow-98 + fn-195 major): user-facing framing is "install the plugin once — your repos need no copies; existing copies can simply be deleted". No benchmark numbers, no speed claims, no external attribution (standing rule).
- Remind Gordon at release time to re-run `install-cursor.sh` / `install-codex.sh` on his machines (standing release step) — after this spec that's the LAST time per-machine reinstalls matter for repo behavior.
- Verify end-state on all four harnesses once more from the released artifacts (not the dev tree): tmp repo, no copies, natural prompt, flowctl resolves from the install.

**Touches:** external properties only (flow-next.dev repo, microsite, vault) + release-notes files per releasing docs
## Acceptance
- [ ] Every property in downstream-properties.md walked; flow-next.dev, microsite/guide, and vault carry the one-mode story with the delete-copies migration note.
- [ ] Release notes drafted in the repo's docs-site format; register/format gates pass; no speed claims or external attribution.
- [ ] Post-release verification: all four harnesses resolve flowctl from their installs in a copy-less tmp repo.
- [ ] Gordon reminded to re-run install-cursor.sh / install-codex.sh.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
