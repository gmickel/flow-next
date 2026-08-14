# Copy-less installs: resolve flowctl from the plugin install on every host; retire copy mode

## Problem

Setup's copy mode duplicates flowctl (launcher, `flowctl.py`, bootstrap, help text, the `flowctl_tracker/` package), `templates/spec.md`, and `usage.md` into every target repo's `.flow/` because Cursor and Grok expose no plugin-root env var. The costs compound: every plugin update requires re-running `/flow-next:setup` per repo to refresh copies; setup carries a two-mode ceremony (Step 2b mode detection, transition/consent table, plugin-refusal invariant); `/flow-next:plan` carries a version-drift check whose only job is policing stale copies; docs carry a dual-mode matrix; and stale copies silently run old flowctl behavior in user repos.

## Evidence (live probes, 2026-08-14)

- **Cursor injects the skill's absolute on-disk path** when a skill loads: `<agent_skill fullPath=".../skills/<name>/SKILL.md" />` (the wrapper also instructs the agent to Read that path). **Grok does the same** via its skill listing (`Absolute path: ...SKILL.md`) — grok loads plugins from the Claude Code install (`~/.claude/plugins/marketplaces/...`). Neither host sets any plugin-root env var, verified by env dumps taken *inside* skill invocations.
- **With one added preamble rung** — derive the plugin root as the directory two levels above the skill's own SKILL.md — natural prompts ("list my flow tasks") resolved and ran the installed flowctl with **no `.flow/bin` present**: cursor-agent CLI (n=1), Cursor desktop app (n=1, human-verified), grok headless (n=1).
- **Codex needs nothing**: its mirror already resolves `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl` first (verified n=1 in a bin-less repo). Claude Code and Droid resolve via `${CLAUDE_PLUGIN_ROOT}` / `${DROID_PLUGIN_ROOT}` already.
- **Version-correctness for free**: the injected path IS the snapshot the harness loaded, so the derivation cannot pick a stale install. A glob probe could: the test machine had a local Cursor install @ 3.33.0 and a stale marketplace cache @ 2.14.0 side by side.
- **Copy-surface audit found no non-agent hard blocker**: Ralph runs off its own self-contained `scripts/ralph/` copy (never `.flow/bin`); the CI example's `.flow/bin` line is commented out; flowctl itself reads repo copies only through tolerant fallbacks that are unreachable when it runs from a plugin tree. One real gap found and scoped: flow-next-tui's resolver has no plugin-install rung (task .3 adds one).

## Design (settled — do not re-litigate)

**Resolution chain.** Every canonical preamble site becomes three rungs, in this order:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

- Rung 1 stays: mechanical and always right on Claude Code / Droid. The env-var probe is NOT removed.
- Rung 2 is new and carries Cursor + Grok. The wording above is the probe-proven wording.
- Rung 3 stays in the chain as a silent backstop only. The product stance is: **copies are dead — everyone deletes them and everything works.** Nothing is documented, tested, or designed around keeping copies; the rung just means a repo that hasn't deleted yet doesn't break mid-migration.
- The Codex mirror keeps `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl` as its rung 1; the mirror ships the same rung-2/rung-3 tail.

**Setup collapses to one mode.** No copies are written, ever. Step 2b's mode ceremony, the transition/consent table, the plugin-refusal invariant, Step 7c's stamp, and Step 8a's variant all go. Setup's remaining jobs: `flowctl init`, the versioned doc snippet via `flowctl setup-block apply`, the config ceremony, optional user-owned seeds (`SPEC.md`, `.flow/criteria.md`), `.codex/agents/*.toml` on Codex, Ralph opt-in, stamps. **Re-running setup is only needed when the snippet schema bumps or config changes — never for plugin updates.**

**Migration message: delete it, everything works.** Two touchpoints, same message:
- `/flow-next:setup` on a repo with leftover copy artifacts detects them (via the reconciled artifact list, single source in flowctl), says they are dead weight on every host, and offers to delete them right there (AskUserQuestion; no silent deletion). The closing summary states when a re-run is ever needed again.
- `/flow-next:plan`'s copy-mode version-drift check is replaced by the same nudge: copy artifacts present → tell the user they can delete them; otherwise silent. The old `setup_version`-vs-manifest comparison is deleted.

**Sweep-settled decisions (three exhaustive sweeps, 2026-08-14; per-file detail lives in the tasks):**
- **`flowctl setup-mode` subcommand is deleted** (parser + `cmd_setup_mode_set`); old `setup_mode`/`setup_version` stamps in `.flow/meta.json` are tolerated as inert metadata, never read. `flowctl-help.txt` is generated and byte-pinned — regenerate it in the same commit.
- **Review-prompt protected-path lists KEEP `.flow/bin/*` verbatim** (`flowctl.py` PROTECTED_ARTIFACTS_BLOCK, the three review workflow files, `agents/quality-auditor.md`, the 8 golden fixtures). Reviewers must never advise deleting a user's committed files; deletion is the user's choice at the setup/plan touchpoints. This also avoids re-pinning the SHA-pinned prompt text and regenerating 8 goldens for zero user value.
- **Gate rules keep their `.flow/bin` entries verbatim** (force-full prefix, cleanliness carve-out, `test_gate_classify` pins): inert residue in copy-less repos, correct behavior in not-yet-migrated ones, zero churn.
- **`flowctl usage` / bootstrap `.flow/usage.md` fallback rungs stay as inert legacy grace** (both resolvers prefer the bundled template; tests that pin the fallback stay).
- **`_stamp_flow_bin_launchers` + the `LAUNCHER_SH`/`LAUNCHER_CMD` constants are deleted** (their only consumer; ralph-init copies from `$PLUGIN_ROOT/scripts/` directly — verified).
- **`PLUGIN_MODE_COPY_ARTIFACTS` is repurposed, not deleted**: reconciled (add `.flow/bin/flowctl_tracker/`) and kept as the machine-readable residue-detection list feeding setup's cleanup offer. Setup workflow lines 134-137 already implement enumerate→remove — the change is promoting it from consent-table gate to unconditional offer.
- **flow-next-tui gains install-location rungs** in `getFlowctlPath` (a copy-less user repo has no `.flow/bin`, no `plugins/` dir, and no PATH flowctl — today's resolver would fail).

**Windows.** `scripts/flowctl.cmd` ships beside `scripts/flowctl` in every install tree, so the derived plugin root finds it — same chain, no special casing. Untested live; verify or note as best-effort in platforms docs.

**Dogfood.** flow-next's own tracked `.flow/bin/`, `.flow/templates/`, `.flow/usage.md` are retired in this spec; `scripts/` becomes the single source. Never touch `.flow/config.json` (line 106 carries a live tracker UUID) or `.flow/` history.

## Out of scope

- Removing the `.flow/bin` fallback rung (never).
- Model tiers / routing (fn-195), review backends (fn-196).
- Editing history: `.flow/specs|tasks|artifacts|memory`, `CHANGELOG.md` entries, `optimization/`, `agent_docs/archive/`, `agent_docs/guidance-eval/`.
- Droid `bin` support verification.

## Risks

- **Prose-followed derivation** (rung 2) is instruction, not mechanism — n=1 per host so far. Mitigations: probe-proven wording verbatim, rung 3 grace, acceptance re-probes.
- **sync-codex.sh is the highest-risk surface.** Three traps, all mapped in task .1/.2: (a) the two fallback-injector awks key on exact string equality with the OLD two-line pattern and would inject a duplicate `.flow/bin` rung into every mirrored file; (b) the setup-workflow strip transform's `skip` region ends on the literal heading `## Step 3: Create .flow/bin/` — deleting that heading without deleting the transform silently truncates the mirrored workflow; (c) four validation guards (~L1936, 1968, 1979, 1988) assert copy-mode/plugin-mode artifacts exist and hard-fail the sync. Every guard pairs with a transform — remove them together.
- **ralph-guard.py's composition screen** exempts the exact current preamble as "standard" (~L798-802); the new rung must join that exemption or Ralph fails closed on every skill invocation.
- **Byte-pinned generated artifacts**: `flowctl-help.txt` (help↔argparse parity test), snippet lockstep tests, mirror parity tests. Regenerate in the same commit as their source change, never hand-edit.
- Cursor team-marketplace installs untested live (mechanism identical — fullPath points into `cache/<sha>/`).
- Markdown anchors: `platforms.md#setup-modes-plugin-vs-copy-fn-121` has 3 inbound links, `agent_docs/setup-modes.md` has 3 — no test covers anchors; task .5 fixes them by hand.
- Release vehicle: behavioral change → rides a batched release; candidate to join the flow-98 + fn-195 major (decide at release time).

## Task graph / wave shape

**All serial: .1 → .2 → .3 → .4 → .5 → .6.** Tasks .1-.3 each regenerate the Codex mirror in-task (canonical + sync rules + mirror + test pins move in the same commit — parity and sync guards stay green at every boundary), so their Touches intersect on `plugins/flow-next/codex/**` and `scripts/sync-codex.sh` by construction. Task .4 touches `.flow/**` (always-serial set). .5 and .6 depend on the final shipped behavior.

## Acceptance (spec level)

- Copy-less repo (`.flow/` data, no `.flow/bin`) is the canonical state: a natural skill prompt succeeds end-to-end on Claude Code, Cursor (CLI + app), Grok, and Codex, each reporting a plugin-install flowctl path.
- Deleting `.flow/bin`, `.flow/templates/spec.md`, and `.flow/usage.md` from a previously set-up repo changes nothing observable in any workflow.
- `/flow-next:setup` writes zero copies; on a repo with leftovers it offers deletion and states when a re-run is ever needed (snippet schema bump / config change — never plugin updates); `flowctl setup-mode` is gone from CLI, help text, and docs; old stamps tolerated on read.
- `/flow-next:plan` on a repo with leftovers shows the delete-me nudge; silent otherwise.
- `./scripts/sync-codex.sh` runs clean twice (idempotent); regenerated mirror carries the three-rung CODEX_HOME-first ladder with no duplicate fallback lines.
- Full gate green (tests incl. retargeted pins, regenerated goldens, docs checks); CI trigger-coverage test green after path-filter removal.
- No shipped doc instructs copying flowctl into a repo; every remaining `.flow/bin` mention is the rung-3 line, the migration/cleanup prose, a protected-path list, a gate-rule residue, or a marked legacy/history note.
