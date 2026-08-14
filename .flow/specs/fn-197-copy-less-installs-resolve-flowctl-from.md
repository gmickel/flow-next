# Copy-less installs: resolve flowctl from the plugin install on every host; retire copy mode

## Problem

Setup's copy mode duplicates flowctl (launcher, `flowctl.py`, bootstrap, help text, the `flowctl_tracker/` package), `templates/spec.md`, and `usage.md` into every target repo's `.flow/` because Cursor and Grok expose no plugin-root env var. The costs compound: every plugin update requires re-running `/flow-next:setup` per repo to refresh copies; setup carries a two-mode ceremony (Step 2b mode detection, transition/consent table, plugin-refusal invariant); `/flow-next:plan` carries a version-drift check whose only job is policing stale copies; docs carry a dual-mode matrix; and stale copies silently run old flowctl behavior in user repos.

## Evidence (live probes, 2026-08-14)

- **Cursor injects the skill's absolute on-disk path** when a skill loads: `<agent_skill fullPath=".../skills/<name>/SKILL.md" />` (the wrapper also instructs the agent to Read that path). **Grok does the same** via its skill listing (`Absolute path: ...SKILL.md`) — grok loads plugins from the Claude Code install (`~/.claude/plugins/marketplaces/...`). Neither host sets any plugin-root env var, verified by env dumps taken *inside* skill invocations.
- **With one added preamble rung** — derive the plugin root as the directory two levels above the skill's own SKILL.md — natural prompts ("list my flow tasks") resolved and ran the installed flowctl with **no `.flow/bin` present**: cursor-agent CLI (n=1), Cursor desktop app (n=1, human-verified), grok headless (n=1).
- **Codex needs nothing**: its mirror already resolves `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl` first (verified n=1 in a bin-less repo). Claude Code and Droid resolve via `${CLAUDE_PLUGIN_ROOT}` / `${DROID_PLUGIN_ROOT}` already.
- **Version-correctness for free**: the injected path IS the snapshot the harness loaded, so the derivation cannot pick a stale install. A glob probe could: the test machine had a local Cursor install @ 3.33.0 and a stale marketplace cache @ 2.14.0 side by side.
- **Copy-surface audit found no non-agent hard blocker**: Ralph runs off its own self-contained `scripts/ralph/` copy (never `.flow/bin`); the CI example's `.flow/bin` line is commented out in favor of fetching `flowctl.py`; flow-next-tui already has four fallback rungs after `.flow/bin`. flowctl itself reads repo copies only through two tolerant fallbacks (`cmd_usage`, `_memory_template_path`) that are unreachable when flowctl runs from a plugin tree.

## Design (settled — do not re-litigate)

**Resolution chain.** Every canonical preamble site becomes three rungs, in this order:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

- Rung 1 stays: it is mechanical and always right on Claude Code / Droid. The env-var probe is NOT removed.
- Rung 2 is new and carries Cursor + Grok. The exact wording above is the probe-proven wording.
- Rung 3 (`.flow/bin`) stays in the chain as a silent backstop only. The product stance is: **copies are dead — everyone deletes them and everything works.** Nothing is documented, tested, or designed around keeping copies; the rung just means a repo that hasn't deleted yet doesn't break mid-migration.
- The Codex mirror keeps its `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl` chain; sync-codex path-patching gains the rung-2 line only if it survives patching cleanly, otherwise the mirror keeps its current two-rung chain (Codex never needs rung 2).

**Setup collapses to one mode.** No copies are written, ever. The Step 2b mode ceremony, the transition/consent table, the plugin-refusal invariant, and Step 7c's copy-materialize path all go. Setup's remaining jobs: `flowctl init`, the versioned doc snippet, the config ceremony, optional user-owned seeds (`SPEC.md`, `.flow/criteria.md`), `.codex/agents/*.toml` on Codex, Ralph opt-in, stamps. **Re-running setup is only needed when the snippet schema bumps.**

**Migration message: delete it, everything works.** Two touchpoints, same message:
- `/flow-next:setup` on a repo with leftover copy artifacts (`.flow/bin/*`, `.flow/templates/spec.md`, `.flow/usage.md`) detects them, says they are dead weight on every host, and offers to delete them right there (AskUserQuestion; no silent deletion). Setup's closing summary also states when a re-run is ever needed again: snippet schema bump or config changes — never plugin updates.
- `/flow-next:plan`'s copy-mode version-drift check is replaced by the same nudge: copy artifacts present → tell the user they can delete them (or let `/flow-next:setup` clean up); otherwise silent. The old `setup_version`-vs-manifest comparison is deleted.

**Windows.** `scripts/flowctl.cmd` ships beside `scripts/flowctl` in every install tree, so the derived plugin root finds it — same chain, no special casing. Untested live; verify or note as best-effort in platforms docs.

**Dogfood.** flow-next's own tracked `.flow/bin/` is retired in this spec (the repo stops copy-mode dogfooding); `test_tracker_distribution.py`, CLAUDE.md contributor instructions, and CI path triggers retarget to `scripts/` as the single source.

## Out of scope

- Removing the `.flow/bin` fallback rung (never).
- Model tiers / routing (fn-195), review backends (fn-196).
- flow-next-tui resolution reorder (already degrades gracefully).
- Droid `bin` support verification.

## Risks

- **Prose-followed derivation** (rung 2) is instruction, not mechanism — n=1 per host so far. Mitigations: probe-proven wording verbatim, rung 3 grace below it, and the acceptance re-probes below.
- **sync-codex SECTION3C heredoc**: the hardcoded heredoc in `scripts/sync-codex.sh` (~line 359-414) rewrites `work/phases.md` §3c in the mirror — canonical edits there are silently dropped unless the heredoc changes in the same commit. Task .1 must check it.
- **Test-pinned literals**: many preamble lines are pinned in `plugins/flow-next/tests/`. Every edited literal: grep tests + sync-codex.sh first, retarget in the same commit, never weaken.
- Cursor team-marketplace installs untested live (mechanism identical — fullPath points into `cache/<sha>/`).
- Release vehicle: behavioral change → rides a batched release; candidate to join the flow-98 + fn-195 major (decide at release time).

## Task graph / wave shape

**All serial: .1 → .2 → .3 → .4 → .5 → .6.** Tasks .1–.3 each regenerate the Codex mirror in-task (canonical + mirror + test pins move in the same commit — parity tests stay green at every boundary), so their Touches intersect on `plugins/flow-next/codex/**` by construction. Task .4 touches `.flow/**` (always-serial set). .5 and .6 depend on the final shipped behavior.

## Acceptance (spec level)

- Copy-less repo (`.flow/` data, no `.flow/bin`) is the canonical state: a natural skill prompt succeeds end-to-end on Claude Code, Cursor (CLI + app), Grok, and Codex, each reporting a plugin-install flowctl path.
- Deleting `.flow/bin`, `.flow/templates/spec.md`, and `.flow/usage.md` from a previously set-up repo changes nothing observable in any workflow.
- `/flow-next:setup` writes zero copies; on a repo with leftovers it offers deletion and states when a re-run is ever needed (snippet schema bump / config change — never plugin updates); `flowctl setup-mode` no longer distinguishes modes (old stamps tolerated on read).
- `/flow-next:plan` on a repo with leftovers shows the delete-me nudge; silent otherwise.
- Full gate green (tests incl. retargeted pins, sync-codex parity, docs checks).
- No shipped doc instructs copying flowctl into a repo, except the legacy migration note.
