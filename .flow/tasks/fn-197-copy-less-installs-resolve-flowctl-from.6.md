# fn-197-copy-less-installs-resolve-flowctl-from.6 Downstream sweep and release notes

## Description
**What:** Downstream sweep + release notes — walk the whole chain per `~/work/agent-instructions/downstream-properties.md`.

**Execution checklist:**
1. Read `~/work/agent-instructions/downstream-properties.md` first and walk every property it lists. Known targets:
   - **flow-next.dev**: install + setup + platforms pages — the copy-mode story comes out everywhere; setup page states the install-once / setup-once-per-repo / re-run-only-on-snippet-bump model; migration note (delete old `.flow/bin`, `.flow/templates/spec.md`, `.flow/usage.md` — nothing depends on them).
   - **Microsite + AI x SDLC guide**: any setup/install references updated to the one-mode story.
   - **Vault** (`~/work/GordonsVault`): update flow-next operational notes touching setup/copies.
2. Release-notes draft for the batched release this rides in (candidate: the flow-98 + fn-195 major), in the repo's docs-site format: user-facing framing is "install the plugin once — your repos need no copies; existing copies can simply be deleted". If `SNIPPET_SCHEMA_VERSION` bumped, the upgrade-actions block says so. No benchmark numbers, no speed claims, no external attribution (standing rule).
3. Remind Gordon at release time to re-run `install-cursor.sh` / `install-codex.sh` on his machines (standing release step) — after this spec that's the LAST per-machine action that affects repo behavior.
4. Post-release verification from the RELEASED artifacts (not the dev tree): tmp repo, `.flow/` data, no copies, natural prompt on all four harnesses (Claude Code, Cursor CLI or app, Grok, Codex) — each resolves flowctl from its install. Also one legacy-shaped repo (leftover `.flow/bin`): everything still works and `/flow-next:plan` shows the delete-me nudge.

**Touches:** external properties only (flow-next.dev repo, microsite, vault) + release-notes files per agent_docs/releasing.md
## Acceptance
- [ ] Every property in downstream-properties.md walked; flow-next.dev, microsite/guide, and vault carry the one-mode story with the delete-copies migration note.
- [ ] Release notes drafted in the docs-site format; upgrade-actions block covers the snippet bump if any; register/format gates pass; no speed claims or external attribution.
- [ ] Post-release verification: all four harnesses resolve flowctl from their installs in a copy-less tmp repo; a legacy-shaped repo still works and plan shows the nudge.
- [ ] Gordon reminded to re-run install-cursor.sh / install-codex.sh.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
