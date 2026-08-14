# fn-197-copy-less-installs-resolve-flowctl-from.3 Retire the copy plumbing in flowctl and replace plan's drift check with the migration nudge

## Description
**What:** Retire the copy plumbing inside flowctl and replace `/flow-next:plan`'s copy-mode drift check with the delete-me migration nudge.

**Details:**
- `scripts/flowctl.py`:
  - Bump `SNIPPET_SCHEMA_VERSION` (~line 20371) to match the converged snippet from task .2.
  - `setup-mode`: collapse to a single mode — keep the subcommand tolerant on read (old `copy`/`plugin` stamps parse fine) but stop enforcing the plugin-refusal invariant (~lines 20375-20383). Decide in-task whether the stamp survives as telemetry or is dropped from new writes.
  - Reconcile `PLUGIN_MODE_COPY_ARTIFACTS`: it omits `.flow/bin/flowctl_tracker/` while setup's artifact list includes it — the reconciled list becomes the leftover-detection list used by task .2 (single source).
  - Remove `_heal_bin_launchers` (~lines 20113-20180) and its `scripts/smoke_test.sh` section (~lines 129-168) — it only ever re-stamped `.flow/bin` launchers.
  - Leave `cmd_usage` and `_memory_template_path` fallbacks as-is (inert when flowctl runs from a plugin tree; harmless tolerance).
- `skills/flow-next-plan/SKILL.md:30` ("Copy-mode version drift"): delete the `setup_version`-vs-manifest comparison and the refresh prompt. Replace with the migration nudge: copy artifacts present → one short line that they're no longer needed and can be deleted (or cleaned by `/flow-next:setup`); absent → silent. Never read/write `version_ack`/`snippet_ack`.
- Optional (do it, it's two lines): drop `ui_version_check` from `skills/flow-next-ralph-init/templates/ralph.sh` (~lines 286-298) — its "run setup to refresh local scripts" advice is now wrong.
- Regenerate the Codex mirror in the same commit; grep tests + sync-codex.sh for pins on every edited literal, retarget same commit.

**Touches:** scripts/flowctl.py, scripts/smoke_test.sh, plugins/flow-next/skills/flow-next-plan/**, plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh, plugins/flow-next/codex/** (regenerated), plugins/flow-next/tests/**
## Acceptance
- [ ] `SNIPPET_SCHEMA_VERSION` bumped in lockstep with the new snippet; `setup-block check` recognizes the new shape.
- [ ] `setup-mode set plugin` refusal invariant gone; old stamps read without error; artifact list unified (includes `flowctl_tracker/`).
- [ ] `_heal_bin_launchers` and its smoke-test section removed; `flowctl init` in a repo without `.flow/bin` creates no bin files.
- [ ] Plan skill: no version comparison remains; nudge appears only when copy artifacts exist and is delete-oriented, not refresh-oriented.
- [ ] `ralph.sh` no longer advises setup re-runs for script refresh.
- [ ] Mirror regenerated + pins retargeted same commit; suite green (exit codes captured directly).
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
