# fn-114 ralph opt-in extraction: guard fixes + no-default-install

> STUB from the fn-101 audit (2026-07-19), expanded same day by maintainer direction: Ralph becomes FULLY optional - nothing Ralph-related installed or firing by default. Supersedes the earlier "feature-freeze only" shape of this spec. Interview/plan before building.

## Goal & Context

Ralph is no longer the default orchestration route (STRATEGY.md: pilot+land is the default; Ralph is the hardened harness for runs that outlast a session) and observed usage is low. Yet every flow-next plugin user pays for it today: hooks.json registers ralph-guard on PreToolUse/PostToolUse/Stop/SubagentStop (the plugin's ONLY hooks - verified fn-101), so every Bash/Edit/Write/Stop event in every session runs the probe shell; repos that ever ran ralph-init additionally spawn Python per event even in normal sessions (the FLOW_RALPH gate lives inside the guard); and every review-subsystem change pays the guard/template extension tax.

Direction: make Ralph a self-contained opt-in add-on. Default install = zero hooks, zero ralph commands in the hot path, zero extension tax.

## Changes

### A. No default install (the core of this spec)

1. **Delete plugins/flow-next/hooks/hooks.json from the plugin.** Hook registration moves into `/flow-next:ralph-init`, which merges the four hook entries into the project's `.claude/settings.json` (careful merge, never clobber existing hooks; idempotent re-run). Claude Code will prompt the user to trust project hooks - that IS the consent gate. Droid: ralph-init writes the Factory-equivalent hooks config (or documents the manual step) - verify current Factory settings path at build time.
2. **Setup surfaces the choice without installing anything**: /flow-next:setup mentions Ralph as available via ralph-init (one line); optionally record `ralph.enabled` in config for skills that care. No yes/no ceremony needed once hooks.json is gone - ralph-init IS the yes.
3. **Uninstall parity**: /flow-next:uninstall and ralph-init --remove (if absent, add) must strip the hook entries from .claude/settings.json.

### B. Extract ralph surface out of flowctl core (the "separate python")

4. Move `flowctl ralph pause/resume/stop/status` (~90 LOC sentinel plumbing) and `find_active_runs` progress.txt parsing (~90 LOC) out of flowctl.py into a repo-local `scripts/ralph/ralphctl.py` (or fold into ralph.sh helpers) installed by ralph-init. `flowctl status` drops its active-runs section, or probes `scripts/ralph/runs/` only when present via a soft import - decide at plan. PRECONDITION: check flow-next-tui for `flowctl ralph status` / active-runs JSON consumers before moving (TUI has Ralph control integration in flight).
5. RALPH_ITERATION receipt stamping stays in flowctl (passive env read, needed by review receipts) but deduped: one `stamp_ralph_iteration(receipt)` helper replaces 10 identical blocks (flowctl.py:24396...27280). Coordinate with fn-112.
6. sync-codex.sh: confirm the codex mirror never shipped hooks (Codex has no Claude-schema hooks); remove any hooks.json handling from the sync script if present.

### C. Guard defect fixes (ride along; the guard still ships, just opt-in)

7. **done-detection**: replace the "done/updated/completed" word sniff (ralph-guard.py:733-740) with a structured signal (tool_response exit code, or require --json and parse it).
8. **Droid mismatch**: Factory hooks reference (re-verified 2026-07-19) still lists `Execute` as canonical for shell (no `Bash`), and Droid file tools are `Edit`/`Create`/`ApplyPatch` (no `Write`). Since registration now happens in ralph-init, write host-appropriate matchers per platform AND make the guard body accept ("Bash","Execute") / ("Edit","Write","Create","ApplyPatch") - or scope Ralph to Claude Code only and say so in ralph.md. Decide at plan.
9. **Write-tool receipt bypass**: extend the Edit|Write handling to block receipt-path writes pre-review (parity with the Bash patterns), or document the Stop-hook as the sole enforcement point and delete the Bash-side ordering theater.
10. **Debug log**: gate the unconditional /tmp append (ralph-guard.py:720-750, 922-955) behind RALPH_GUARD_DEBUG=1; use tempfile.gettempdir() (Windows parity, ralph-guard.py:34).
11. **Dead weight**: delete RALPH_GUARD_VERSION no-op constant; delete or wire `ralph_e2e_test.sh` into local-dev.md; delete the rp pick-window state-file write + stale docstring (flowctl.py:20389/20287) if fn-111 has not already.
12. **find_active_runs**: parse progress.txt via key=value contract lines (extend ralph.sh's existing `promise=COMPLETE` pattern) instead of prose regex - lands wherever the code moves per item 4.

### D. Docs

13. ralph.md: opt-in install story, guard-rules table completeness, fix the state.json claim (PAUSE/STOP sentinels + progress.txt), zero-overhead claim becomes literally true. platforms.md: note the per-host hook installation difference. CLAUDE.md cross-platform checklist: hooks row updated (no plugin-level hooks; ralph-init owns registration).

## Acceptance

- Fresh plugin install registers ZERO hooks; no ralph-guard process spawns in any session until ralph-init has been run AND the user approved the project hooks.
- Post ralph-init: ralph smoke + e2e-short suites green; guard blocks/permits unchanged on Claude Code happy paths.
- Zero /tmp writes and zero Python spawns from hooks when FLOW_RALPH unset (test).
- flowctl.py contains no `cmd_ralph_*` functions (or documented soft-probe remainder per item 4 decision).
- TUI consumer check recorded; Droid decision recorded and files consistent.

## Boundaries

- No new guard capabilities. fn-55 delegation allowlist untouched (audit verdict: exemplary).
- Ralph stays supported and documented - this spec changes WHERE it lives and WHO pays for it, not what it does.
- 3.0 extract-to-separate-repo/sunset decision still deferred; this spec is the halfway house that makes either endgame cheap.
