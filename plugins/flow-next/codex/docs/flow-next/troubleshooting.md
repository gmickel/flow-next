# Troubleshooting

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


Common recovery patterns for stuck tasks, broken state, Ralph debugging, and review-backend conflicts. For deeper subsystem guides see [`flowctl.md`](flowctl.md) (CLI reference), [`ralph.md`](ralph.md) (Ralph internals), and the parent [`../README.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/README.md).

## Contents

- [Updated the plugin: do I re-run setup?](#updated-the-plugin-do-i-re-run-setup)
- [I have `.flow/bin/` from an old install](#i-have-flowbin-from-an-old-install)
- [Pre-1.0 layout porting](#pre-10-layout-porting)
- [Reset a stuck task](#reset-a-stuck-task)
- [Clean up `.flow/` safely](#clean-up-flow-safely)
- [Debug Ralph runs](#debug-ralph-runs)
- [Receipt validation failing](#receipt-validation-failing)
- [Pilot keeps skipping a spec the board says is ready (strikes ledger, fn-184/#325)](#pilot-keeps-skipping-a-spec-the-board-says-is-ready-strikes-ledger-fn-184325)
- [Review loop stalls, repeats unchanged work, or runs away (fn-90/fn-159)](#review-loop-stalls-repeats-unchanged-work-or-runs-away-fn-90fn-159)
- [flowctl says my config carries removed keys, or my routing block is ignored (fn-195)](#flowctl-says-my-config-carries-removed-keys-or-my-routing-block-is-ignored-fn-195)
- [Review reports a model downgrade / floor (fn-76 resolution ladder)](#review-reports-a-model-downgrade-floor-fn-76-resolution-ladder)
- [Worker reports a merge conflict at wave join (fn-176 wave dispatch)](#worker-reports-a-merge-conflict-at-wave-join-fn-176-wave-dispatch)
- [Custom RepoPrompt CLI instructions conflicting](#custom-repoprompt-cli-instructions-conflicting)
- [Copilot review backend on Windows (fixed in 1.1.9)](#copilot-review-backend-on-windows-fixed-in-119)
- [Windows: `python3` not found / Microsoft Store alias stub (fixed in fn-77)](#windows-python3-not-found-microsoft-store-alias-stub-fixed-in-fn-77)
- [`/flow-next:map`: clawpatch not found / version mismatch / Node 20](#flow-nextmap-clawpatch-not-found-version-mismatch-node-20)
- [Uninstall](#uninstall)
- [Cursor in-IDE browser MCP missing (`cursor-ide-browser`)](#cursor-in-ide-browser-mcp-missing-cursor-ide-browser)
- [Renamed skill: `browser` → `flow-next-drive` (1.4.0)](#renamed-skill-browser-flow-next-drive-140)
- [Rolling-frontier scheduling (`/flow-next:work` default route)](#rolling-frontier-scheduling-flow-nextwork-default-route)
- [See also](#see-also)

## Updated the plugin: do I re-run setup?

**No.** Setup copies nothing into your repo, so a plugin update (`/plugin` update, `droid plugin update`, or `git pull` + re-install on Codex/Cursor) is the whole update: every skill resolves `flowctl` from the plugin install itself, and the agent guide comes from `flowctl usage`. Re-run `/flow-next:setup` only when setup tells you the docs-snippet schema bumped, or when you want to change configuration or re-seed the user-owned files. It stays idempotent and non-destructive (your specs/tasks/memory/config are untouched). See [platforms.md → What setup does](platforms.md#what-setup-does).

## I have `.flow/bin/` from an old install

Delete it. `.flow/bin/`, `.flow/templates/spec.md`, and `.flow/usage.md` are snapshots from the retired copy layout; nothing reads them, and removing them changes nothing observable in any workflow. One exception before you bulk-delete: a `.flow/templates/spec.md` you EDITED is your content - copy it to a repo-root `SPEC.md` first (that is the customization point now); setup's cleanup offer detects a differing template and never deletes it for you. Keeping them is a hazard, not a safety net - a stale copied `flowctl` can shadow the current one (a flag that "should exist" erroring is the classic symptom). `/flow-next:setup` detects the leftovers and offers to delete them (`/flow-next:plan` prints a one-line nudge and moves on); you can also just `rm -rf .flow/bin .flow/templates/spec.md .flow/usage.md` (use `git rm` for tracked copies).

## Pre-1.0 layout porting

`flowctl migrate-rename` / `migrate-rollback` are gone. Port by hand: rename `.flow/epics/` -> `.flow/specs/`, rewrite `next_epic`/`epic`/`epic_id` keys per `flowctl usage` "Pre-1.0 layout porting", then `flowctl validate --all`.

## Reset a stuck task

```bash
# Check task status
flowctl show fn-1.2 --json

# Reset to todo (from done/blocked)
flowctl task reset fn-1.2

# Reset + dependents in same spec
flowctl task reset fn-1.2 --cascade
```

`--cascade` walks the spec's `depends_on` graph and resets every downstream task that referenced the target, so the next `flowctl ready` call surfaces them again.

## Clean up `.flow/` safely

Run manually in terminal (not via AI agent - destructive command guards block agents from running `rm -rf`):

```bash
# Remove all flow state (keeps git history)
rm -rf .flow/

# Re-initialize
flowctl init
```

Or run `/flow-next:uninstall` to clean up docs and get the commands printed for manual execution.

## Debug Ralph runs

```bash
# Check run progress
cat scripts/ralph/runs/*/progress.txt

# View iteration logs
ls scripts/ralph/runs/*/iter-*.log

# Check for blocked tasks
ls scripts/ralph/runs/*/block-*.md
```

Each Ralph run lives under `scripts/ralph/runs/<timestamp>/`. The directory contains the iteration log, receipts (review / walkthrough / blocked), and an optional `progress.txt` tail. Deep dive: [`ralph.md`](ralph.md).

## Receipt validation failing

```bash
# Check receipt exists
ls scripts/ralph/runs/*/receipts/

# Verify receipt format
cat scripts/ralph/runs/*/receipts/impl-fn-1.1.json
# Must have: {"type":"impl_review","id":"fn-1.1",...}
```

Ralph reads receipts to decide whether to advance, retry, or block. A missing or malformed receipt freezes the loop. The bundled `flowctl validate --all` checks state-file shape; receipt-shape errors usually mean a backend wrote the file mid-iteration and the loop crashed.

## Pilot keeps skipping a spec the board says is ready (strikes ledger, fn-184/#325)

**Symptom:** `/flow-next:pilot` printed `PILOT_VERDICT=BLOCKED ... reason="no advancement (strike 2/2, spec unreadied): ..."` on an earlier tick, and now every tick skips that spec - even though the issue sits in the ready state on the board and `flowctl show <spec-id>` reports `ready: true`.

**Why:** pilot records a **strike** for each healthy no-advance tick in a ledger at `<git-common-dir>/flow-next/pilot-strikes.json` (shared across worktrees, never committed - it lives under `.git/`). At strike 2/2 it runs `spec unready`. On a repo with `tracker.readyState` configured, the next tracker pull projects the board state back and re-readies the spec - but **a projection-set ready does not clear a strike** (fn-87 R7): the echo re-grants readiness with no human involved, and clearing on it would re-dispatch the same failing spec forever. So the spec reads ready everywhere a human looks while pilot keeps it struck.

**Inspect and recover:**

```bash
# What is struck, why, and when
flowctl pilot strikes list
flowctl pilot strikes list --json

# Recognized human clear (after you have actually addressed the failure)
flowctl pilot strikes clear <spec-id>

# Wipe the whole ledger (e.g. after a batch of unrelated failures)
flowctl pilot strikes clear --all
```

Clearing a strike **does not re-ready the spec** - the two signals are orthogonal. On a `readyState` repo the board (or the next pull) owns readiness; on a repo without it, run `flowctl spec ready <spec-id>` yourself. Fix the underlying failure first: the strike reason in `strikes list` names the stage and what did not advance.

## Review loop stalls, repeats unchanged work, or runs away (fn-90/fn-159)

**Symptoms:** a plan/impl/completion review loops far more than the ~3-round cap - the field report was **~11×** on a large ticket before the reviewer and implementer converged. Most common on the **Cursor** review backend, but the underlying causes were backend-agnostic.

**What was happening (root causes, now bounded):**
- **The cap was prose-only and reset every invocation.** `MAX_REVIEW_ITERATIONS` (then default 4; now 8) was an instruction to the host LLM to keep an in-context counter - but it reset to 0 on every *fresh* review invocation (a new Ralph iteration, a new pilot tick, a human retry). The runaway was ≈ 5-6 fresh invocations × ~3 in-agent rounds. Now flowctl owns a **cumulative counter on spec state** that survives fresh invocations and **refuses at the cap** (exit `4` + `ESCALATE:`).
- **Every re-review was a fresh blind review** (a churn lottery - two identical fresh Cursor reviews overlapped on only ~50% of findings, so SHIP was statistically near-unreachable within the cap). The **convergence ratchet** now renders the validated `findings.items` records (severity, classification, and status) with labeled legacy prose only as a fallback. Its shrink-only contract remains: verify each prior finding fixed; only a NEW ≥ Major finding may block; all prior fixed + no new ≥ Major ⇒ MUST SHIP.
- **Codex/copilot verdicts could be poisoned** by a verdict literal echoed in tool output (e.g. a grep of `smoke_test.sh`'s assertions), making flowctl report SHIP while the reviewer said NEEDS_WORK - a false SHIP *or* a false NEEDS_WORK that kept a loop alive. The parse now isolates the final agent message (last-match).
- **The ratchet asked for prior-finding resolutions without stating the machine grammar**, so a compliant-sounding reviewer answered in prose and the parser recorded nothing: every prior carried forward at `open`, the open set looked inflated, and a trend-based stall rule escalated three healthy converging loops in a row at round 2 of 8. The prompt now states the exact line grammar (and an aggregate all-clear), the parser accepts every token it advertises, and **the trend rules are gone** - see the note below on what a runaway looks like now.
- **Cursor's ambient injection** (its built-in persona rubric + auto-attached `AGENTS.md`) diluted the scope anchor. A **persona-override preamble** now rides in every cursor review prompt (see [`orchestration.md`](orchestration.md)).

**What to do if you hit the cap now:**
- `NOT_RETRYABLE: artifact unchanged since last verdict` exits **1** before dispatch and consumes no round. Change the actual reviewed artifact, or have a human decide whether an explicit re-plan is warranted; do not blindly retry it.
- Either `ESCALATE: review loop stalled (<rule>)` or `ESCALATE: reviewer requested human review` exits **4** and is **not retryable**. Under Ralph/autonomous it surfaces as NEEDS_HUMAN. A human should inspect the persisted receipt and findings trail, then decide whether the work needs redesign, a focused fix, or a re-plan.
- After an explicit **re-plan** (you rewrote the spec/approach, not just patched a finding), a human can reset the counter to re-open the cap: `flowctl spec reset-review-rounds <spec-id>` (add `--impl` to also clear per-task impl-review counters). A `SHIP` verdict resets automatically. Ralph blocks reset commands and `--force`; they are never autonomous recovery tools.
- **A loop that runs to the cap with no early escalation is now the expected shape for a non-compliant reviewer, not a bug.** Only one rule terminates early - the reviewer explicitly marking the same finding `not-fixed` in two consecutive rounds - and it needs the machine grammar (`Prior finding #2: not-fixed`) to fire. A reviewer that resolves priors in prose produces no such evidence, so the cap is its only bound. That is deliberate: the trend heuristics this replaced turned non-compliance into *wrong* early stalls instead of *expensive* ones. If the cost bites, **lower the cap - do not re-add trend inference** (the reasoning is recorded in `.flow/memory/knowledge/decisions/`).
- The default is 8, resolved as env `MAX_REVIEW_ITERATIONS` > config `review.maxIterations` > 8. Tune it with `flowctl config set review.maxIterations <n>` for a persistent change; the cap remains enabled (minimum 1) and escalation remains preferable to a larger budget. Under Ralph both rungs are human-only.
- Full semantics: [`flowctl.md` § Deterministic review cap](flowctl.md#codex-impl-review) and [`ralph.md` § Review Loops Until SHIP](ralph.md#3-review-loops-until-ship).

## flowctl says my config carries removed keys, or my routing block is ignored (fn-195)

**Symptom:** one non-blocking line like

```
note: .flow/config.json still carries removed key(s): models.roles, models.verifiedAt; flowctl ignores them. Routing is now the model-routing block /flow-next:setup writes into CLAUDE.md / AGENTS.md plus the recipes in `flowctl usage` - route work there and delete these keys.
```

**This is expected, not an error.** The role map (`models.roles`) and its staleness stamps (`models.verifiedAt` / `models.verifiedWith`), like the `work.delegate*` keys, are removed - flowctl reads none of them. The advisory prints at most once per invocation, on the config and work entry points only, and never blocks. Delete the keys when convenient.

**Routing not taking effect?** Routing is prose read by the agent, not config parsed by flowctl, so check in this order:

- **The block is in the file the host actually reads** (`CLAUDE.md` on Claude Code / Droid / Grok, `AGENTS.md` on Codex / Cursor / Grok - see [`platforms.md`](platforms.md)), and its lines are **uncommented**. `/flow-next:setup` writes every line commented out on purpose; nothing routes until you uncomment one.
- **The grammar is `<tier>: <model>`** (optionally `at <effort>`), with a tier name from the four: `reviewer`, `implementer`, `fast scout`, `thinking scout`. An unrecognized name is treated as unset with one advisory; an unparseable line is ignored.
- **Something higher in the precedence chain won.** Highest first: an explicit instruction in the invocation, then the routing block, then the agent definition's own default, then the session model. A model this harness cannot reach falls back to the session model, says so once, and continues - routing never fails closed.
- **The harness may not have that reach at all.** Check its page under [`reach/`](reach/README.md): a host with no subagent primitive and no second CLI runs the work in session, and that is the documented degradation, not a fault.
- **Check what actually ran.** Stage records carry the model where the harness exposes it - an absent value means unknown, never the configured value.

## Review reports a model downgrade / floor (fn-76 resolution ladder)

**Symptom:** a review prints one stderr line like

```
warning: codex model '<ranking top>' unavailable; downgraded to '<next in ranking>'. Cached temporarily for this CLI version and routing intent.
```

(or `… fell back to the never-fail floor (the CLI default / 'auto')`), and the review's receipt records the model actually used / `auto` / `default` rather than the ranking top.

**This is expected, not an error.** flow-next dispatches the *strongest* model by default and, when the local CLI can't run it, transparently resolves the best available one (the [model-resolution ladder](flowctl.md#model-resolution-strongest-available-never-fail-fn-76)). It fires ONLY on the distinctive model-unavailable signature (codex *"requires a newer version of Codex"*, copilot *`… from --model flag is not available`*, cursor *`Cannot use this model: …`*); auth / network / sandbox / timeout failures propagate unchanged.

**What to do:**
- **Want the top model?** Upgrade the backend CLI - a ranking top can require a newer CLI than the one installed. The cache key is `(backend, CLI version, effective routing intent)`, so a CLI or routing change re-resolves automatically on the next review.
- **The downgrade repeats every review?** It normally should not - the result is memoized in `.flow/.cache/model-resolution.json`. A changed routing role, CLI version, or the 24-hour stronger-model re-probe intentionally causes one fresh resolution. Otherwise, the cache file may be unwritable; check permissions.
- **Force a specific model** (skip the ladder + cache entirely): pin it explicitly - `--spec codex:<model>`, a per-task/per-spec `review:` value, `FLOW_CODEX_MODEL`, or `review.backend`. An explicit unavailable model errors clearly instead of downgrading.
- **Reset the cache:** `rm -rf .flow/.cache/` - it is regenerated (and gitignored) on the next review; a corrupt file is already treated as a cold start.

## Worker reports a merge conflict at wave join (fn-176 wave dispatch)

**Symptom:** a concurrent wave's workers all finished green in their own workspaces, but the conductor hits a merge conflict while joining one of their commits onto the target branch.

**Why:** the wave is dispatched from each task's `**Touches:**` declaration, and dispatch assumes those file sets are disjoint. A conflict at join means two tasks in the wave actually wrote the same file - the declarations were wrong (or incomplete), not the merge.

**What to do:** resolve the conflict, then re-run the affected task serially so it builds on the other task's committed result instead of racing it. Correct the `**Touches:**` lists on the tasks involved before the same pair is dispatched together again. Nothing was corrupted: each worker ran in an isolated workspace against a committed base, so the conflict is surfaced at the join rather than silently interleaved.

## Custom RepoPrompt CLI instructions conflicting

> **Caution**: If you have custom RepoPrompt CLI instructions in your `CLAUDE.md` or `AGENTS.md`, they may conflict with Flow-Next's integration.

Flow-Next's plan-review and impl-review skills include specific instructions for CE-first CLI discovery, window selection, builder workflow, and chat commands. Custom instructions can override these and cause unexpected behavior.

**Symptoms:**
- Reviews not using the correct RepoPrompt window
- Builder not selecting expected files
- Chat commands failing or behaving differently

**Fix:** Remove or comment out custom RepoPrompt CLI instructions from your `CLAUDE.md`/`AGENTS.md` when using Flow-Next reviews. The plugin provides the complete CE-first workflow.

> **Note:** RepoPrompt is macOS-only. When the CE-first ladder (`rpce-cli`, the two CE user links, then Classic `rp-cli`) finds no runnable candidate, `/flow-next:plan` and the review skills do not propose RepoPrompt. Explicit `--review=rp` is still accepted and errors at runtime if no supported RepoPrompt CLI is available.

## Copilot review backend on Windows (fixed in 1.1.9)

Spec-driven `flowctl copilot {impl,plan,completion}-review` calls work on native Windows from 1.1.9 onwards. No action required - the WSL detour from the 1.1.8 era is no longer necessary.

**What changed:** the POSIX path passes the prompt via `copilot -p "<text>"` (argv) which collides with Windows' `CreateProcessW` 32,767-char limit for spec-sized prompts. From 1.1.9, `run_copilot_exec` detects `sys.platform == "win32"` and switches to stdin delivery (`subprocess.run(input=prompt, ...)`) - bypassing the argv cap entirely. Stdin-mode `--resume` is resume-only (unlike `-p` mode's create-or-resume), so flow-next uses `--session-id=<uuid>` on the first call and `--resume=<uuid>` afterwards, tracked via a touch marker under `.flow/tmp/copilot-sessions/<uuid>`.

POSIX (macOS / Linux / WSL) behavior is unchanged.

**If you still see Windows argv errors:** inspect the installed plugin version in your host's plugin manager and update Flow-Next - every repo consumes the updated launcher directly, so no per-repo re-run is needed. If the repo still carries a legacy `.flow/bin/` copy, delete it (see [I have `.flow/bin/` from an old install](#i-have-flowbin-from-an-old-install)); a stale copy shadows the fixed launcher.

**Upstream:** [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) tracks a first-class `--prompt-file` flag. Once that lands, both POSIX and Windows paths will move to the cleaner file-based delivery.

## Windows: `python3` not found / Microsoft Store alias stub (fixed in fn-77)

**Symptom:** on Windows, `flowctl` fails with *"Python was not found; run without arguments to install from the Microsoft Store…"* and exit code **9009**, even though you installed real Python.

**Cause:** `python3` resolves to the Microsoft Store **App Execution Alias** - a 0-byte reparse point at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` that Windows ships **enabled by default**. When your real Python came from [python.org](https://python.org) or the `py` launcher (not the Store), the stub shadows it: it satisfies `command -v python3` (it *is* on `PATH`) but is non-functional. Older flowctl launchers trusted presence over function and picked the stub - so flow-next broke on every Windows machine in this configuration.

**The shipped fix (no action needed on a fresh install):** the `flowctl` launchers now probe interpreter functionality **and require Python 3.11+** in order `$PYTHON_BIN` → `py -3` → `python3` → `python`, so the 9009 stub and working-but-too-old interpreters are skipped before `flowctl.py` loads. If no candidate works, the error says so; if candidates work but are below 3.11, a distinct error tells you to install or select a supported Python. A `flowctl.cmd` batch shim ships alongside the extensionless bash `flowctl`, so PowerShell / cmd.exe (Claude Desktop, native Codex, native Cursor) resolve a supported interpreter too. See [`platforms.md` → Windows: Python discovery](platforms.md#windows-python-discovery).

**Recovering a legacy copied install** (a pre-fix `.flow/bin/flowctl` hardcodes `exec python3` and cannot fix itself). This only applies to repos still carrying the retired copy layout. Pick either:

1. **Delete the copy (recommended, durable).** The plugin's own launchers already carry the fix, and nothing reads `.flow/bin/` any more:

   ```powershell
   Remove-Item -Recurse -Force .flow\bin        # git rm -rq .flow/bin if it is tracked
   ```

   After this, `flowctl` and `flowctl.cmd` resolve from the plugin install and work in every shell. `/flow-next:setup` offers the same deletion interactively.

2. **Disable the Store alias (per-machine OS workaround).** Settings → Apps → Advanced app settings → **App execution aliases** → toggle **OFF** for `python.exe` **and** `python3.exe`. `python3` then resolves to your real install. Note the `py` launcher is [not included with Store Python](https://learn.microsoft.com/windows/python/faqs), so if you were relying on Store Python, install python.org Python (which ships `py`) to get `py -3`.

Prefer path 1 - the alias toggle is per-machine, not durable, and does not survive a fresh Windows profile.

**Sources:** Microsoft Learn [Python on Windows FAQ](https://learn.microsoft.com/windows/python/faqs) (the App Execution Alias stub + "the py launcher is not included with Store Python" + disabling the alias); python.org [Using Python on Windows](https://docs.python.org/3/using/windows.html) and [PEP 397](https://peps.python.org/pep-0397/) (the `py` launcher / `py -3`).

## `/flow-next:map`: clawpatch not found / version mismatch / Node 20

`/flow-next:map` wraps the upstream `clawpatch` CLI. Three common failure modes:

**1. `clawpatch` binary missing.** Skill prints `pnpm add -g clawpatch` install instructions verbatim and exits 1. No auto-install - global npm/pnpm installs are user-consent territory.

```bash
# Recommended: install globally with pnpm
pnpm add -g clawpatch
```

**2. pnpm installed `clawpatch` but it's not on PATH.** pnpm installs global binaries under `$PNPM_HOME` and needs a one-time `pnpm setup` to wire PATH - without it, the install lands but the binary isn't resolvable. (Exact location varies by pnpm version and OS: `~/.local/share/pnpm` on many setups, `$PNPM_HOME/bin/` on others - `pnpm bin -g` reports yours.) Skill detects `pnpm bin -g` exit-0 + `command -v clawpatch` exit non-zero and prints the PNPM_HOME hint:

```bash
pnpm setup            # writes PNPM_HOME + adds it to your shell rc
source ~/.zshrc       # or ~/.bashrc — pick up the new PATH entry
command -v clawpatch  # should now resolve
```

**3. `clawpatch --version` falls outside the tested range.** The skill carries a single-source `SUPPORTED_CLAWPATCH` version range in its prose; see `plugins/flow-next/skills/flow-next-map/SKILL.md` for the current pin. Outside range emits a one-line stderr warning naming expected vs found and continues (degrades - never blocks). Re-pin lands on each clawpatch minor.

**4. Node 20 with `clawpatch` installed.** clawpatch's `engines.node: ">=22"` triggers its own error; the skill propagates it verbatim. Upgrade Node 22+ (e.g. `nvm install 22 && nvm use 22`) or skip `/flow-next:map` - scouts gracefully fall back to the grep/glob path when `.clawpatch/` is absent.

**5. "Should I commit `.clawpatch/` to the repo?"** No - by default the skill writes a `.clawpatch/.gitignore` with `*` + `!.gitignore`, making the feature index local-per-developer. The map is regenerable from `clawpatch map`, the schema may flip between pre-1.0 minor releases, and committing it creates PR review noise + merge conflicts. See [Sharing contract](../../skills/flow-next-map/SKILL.md#sharing-contract-local-only-by-design) in the skill prose, or the full trade-off table at [flow-next.dev/skills/map](https://flow-next.dev/skills/map/). Teams that want shared indexes can customize the skeleton - unsupported, but the skill won't clobber a customized `.gitignore` on re-run.

The skill is **opt-in convenience** - `flowctl` core never imports or requires clawpatch; nothing else in flow-next breaks when the skill can't run.

## Uninstall

Run manually in terminal (DCG blocks these from AI agents):

```bash
rm -rf .flow/               # Core flow state
rm -rf scripts/ralph/       # Ralph (if enabled)
```

Or use `/flow-next:uninstall` which cleans up docs and prints commands to run. Doc cleanup removes two independent marker blocks from `CLAUDE.md`/`AGENTS.md`: the `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` instructions block and, if `/flow-next:setup` scaffolded one, the `<!-- flow-next:model-routing:start -->` … `<!-- flow-next:model-routing:end -->` model-routing block (removed only when its marker pair is well-formed - a damaged pair is reported and left untouched). `GLOSSARY.md` and `STRATEGY.md` at the repo root are intentionally preserved - they outlive flow-next per the survives-uninstall invariant.

## Cursor in-IDE browser MCP missing (`cursor-ide-browser`)

Drive / QA on Cursor probes the built-in browser by exact MCP id `cursor-ide-browser`. A catalog miss is not absence. If the probe still fails:

1. Settings → Tools & MCP → **Browser Automation** = Browser Tab.
2. In chat, type `@Browser` (no space), or open the Browser pane until it shows connected.
3. Re-run the probe (`browser_tabs` list). One re-probe after that is enough; do not loop.

A mid-run `MCP server does not exist: cursor-ide-browser` after the pane was already driving is a known Cursor flake, not a first-use miss. `@Browser` does not restore that session. Quit Cursor fully (Cmd-Q), wait ~10s, confirm the Browser pane shows connected, then start a **fresh chat**. Detail: [`platforms.md`](platforms.md) and [`cursor-ide-browser.md`](../../skills/flow-next-drive/references/cursor-ide-browser.md).

## Renamed skill: `browser` → `flow-next-drive` (1.4.0)

The `browser` skill was renamed `flow-next-drive` in 1.4.0 (surface-aware driver ladder). The invocation is now `/flow-next:flow-next-drive`; the Codex mirror is also `flow-next-drive` (previously `agent-browser`, which collided with the user's global `agent-browser` skill and Codex-native browser skills).

If a cached install still surfaces an orphaned `browser` / `agent-browser` skill after upgrading, it auto-clears within ~7 days as the plugin cache refreshes. To clear it immediately, delete the stale cached marketplace directory under the Claude plugin cache path:

```bash
rm -rf ~/.claude/plugins/cache/<marketplace>   # then reload Claude Code
```

## Rolling-frontier scheduling (`/flow-next:work` default route)

`/flow-next:work` schedules on the rolling frontier by default and prints the route once during Phase 3, before the first claim - the wave form at entry, the rolling form after the scheduler's dispatch probe (`Scheduling: rolling`, or `Scheduling: wave (<reason>)`). Most failures resolve exactly as wave-route failures do. Route-specific ones:

- **`Scheduling: wave (planSync.enabled=true)`** - plan-sync's per-wave barrier is a fail-closed rule, so a repo that opted into plan-sync runs the wave loop. **`false` is the shipped default since 4.5.1** (earlier inits wrote `true`), so this fires only on repos that opted in: rolling needs `flowctl config set planSync.enabled false`. The run never mutates config itself.
- **`Scheduling: wave (task-id run | single task | sequential dependency chain)`** - the run was given a task id (the wave route runs exactly that task), the spec has fewer than two open tasks, or no two open tasks are dependency-independent; one lane has nothing for rolling admission to schedule, so the single-worker wave path runs it with less machinery. Not an error.
- **`Scheduling: degraded to wave (host lacks non-blocking dispatch)`** - the host's subagent dispatch was measured to block until completion, so the rolling overlap is lost; the rest of the rolling lifecycle (isolated workspaces, conductor-owned review, notes surface) still runs. See the [platforms matrix](platforms.md).
- **A task is held or dropped as claimed by another actor** - task claims live in the shared runtime state store and are spec-scoped, so two runs on the same spec contend on the same claims and fail closed against each other. That is the designed behavior, not a bug. Do not clear or steal another run's claim; if the other run is truly dead, recover with the human-only repair in [Reset a stuck task](#reset-a-stuck-task).
- **`Notes surface: unavailable (...)`** - the shared run-notes directory could not be created. Advisory only: the run continues without it, nothing blocks. A notes dir abandoned by an interrupted run (under `<state-root>/flow-notes/`, see [`architecture.md`](architecture.md#outside-tree-runtime-state-and-run-notes-dirs)) is inert markdown and safe to delete by hand.
- **A worker reports a merge conflict at integration** - per-task integration reuses the wave-join mechanics; the conflicting task is retried serially, never a correctness loss. Same handling as [the wave-join section above](#worker-reports-a-merge-conflict-at-wave-join-fn-176-wave-dispatch).

## See also

- [`flowctl.md`](flowctl.md) - full CLI reference (every command, flag, default).
- [`ralph.md`](ralph.md) - Ralph loop internals + DCG setup.
- [`platforms.md`](platforms.md) - platform-specific gotchas (Droid, Codex, OpenCode).
- [`sync-codex.md`](sync-codex.md) - Codex mirror regeneration + validation guards.
