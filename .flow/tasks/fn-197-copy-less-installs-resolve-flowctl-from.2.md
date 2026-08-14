# fn-197-copy-less-installs-resolve-flowctl-from.2 Collapse setup to one copy-less mode, converge the doc snippets, add the leftover-cleanup offer

## Description
**What:** Collapse `/flow-next:setup` to a single copy-less mode, converge the doc snippets on the plugin shape, and add the leftover-cleanup offer plus the "when to re-run setup" message.

**Details (in `skills/flow-next-setup/workflow.md` unless noted):**
- Delete the copy machinery: Step 3 + Step 4 copy blocks (`.flow/bin/*` incl. `flowctl_tracker/` + `verify_tracker_manifest` call, `.flow/templates/spec.md`, `.flow/usage.md`), Step 2b mode ceremony, the transition/consent table (lines ~111-146), Step 7c's copy-materialize-on-refusal branch, the Step 8a variant, and every `MODE=copy|plugin|plugin-kept` branch.
- **Leftover detection (user-facing):** when the repo carries copy artifacts (`.flow/bin/*`, `.flow/templates/spec.md`, `.flow/usage.md`), tell the user during setup that these are dead weight on every host — deleting them changes nothing — and offer to delete them via AskUserQuestion. Never delete silently.
- **Re-run guidance:** setup's closing summary states plainly when a re-run is actually needed — the doc-snippet schema bumped or the user wants to change config/seeds — and that plugin updates no longer require any per-repo action.
- Snippet convergence: retire the `.flow/bin` spellings from `templates/claude-md-snippet.md` and `templates/agents-md-snippet.md`; converge on the `claude-md-snippet-plugin.md` shape (bare `flowctl` + resolution chain shown once + `<!-- flow-next:snippet:vN -->` sentinel), with a `$flow-next-` command-syntax variant for Codex. One snippet family, host-variant only in command syntax.
- `templates/usage.md`: bare `flowctl` spellings throughout (the line-5 escape hatch becomes the norm).
- `templates/model-routing-snippet.md:29`: drop its `.flow/usage.md` mention.
- `commands/uninstall.md`: collapse the copy-mode branch into the plugin-mode one; drop the stale `version_ack`/`snippet_ack` mention.
- Keep untouched: `SPEC.md` seed (Step 4a), `.flow/criteria.md`, `.codex/agents/*.toml` on Codex, Ralph opt-in, config ceremony, stamps.
- Regenerate the Codex mirror in the same commit; retarget test pins in the same commit (setup's workflow is heavily pinned — grep first).

**Touches:** plugins/flow-next/skills/flow-next-setup/**, plugins/flow-next/templates/**, plugins/flow-next/commands/uninstall.md, plugins/flow-next/references/**, plugins/flow-next/codex/** (regenerated), plugins/flow-next/tests/**
## Acceptance
- [ ] Setup workflow contains no copy step: fresh-repo setup writes `.flow/` state, snippet, config, optional seeds — zero files under `.flow/bin/`, no `.flow/templates/spec.md`, no `.flow/usage.md`.
- [ ] Mode ceremony gone: no `MODE`/`plugin-kept` branches, no transition/consent table, no copy-materialize path; setup reads old `setup_mode` stamps without erroring.
- [ ] Leftover artifacts detected → user told they're deletable + AskUserQuestion offer; declining proceeds normally.
- [ ] Closing summary states the only re-run triggers (snippet schema bump, config/seed changes) and that plugin updates need no per-repo action.
- [ ] `claude-md-snippet.md` / `agents-md-snippet.md` / `usage.md` contain no `.flow/bin` spellings; snippet carries a version sentinel; Codex variant uses `$flow-next-` syntax.
- [ ] `commands/uninstall.md` single-branch; no `version_ack`/`snippet_ack` mention.
- [ ] Codex mirror regenerated same commit; test pins retargeted same commit; suite green.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
