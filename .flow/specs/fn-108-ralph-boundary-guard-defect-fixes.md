# fn-108 ralph boundary: guard defect fixes + feature-freeze declaration

> STUB from the fn-101 audit (2026-07-19). Cuts the Ralph extension tax and fixes three real guard defects. The 3.0 extract-or-sunset decision is explicitly NOT made here.

## Goal & Context

Ralph's flowctl-core footprint is small (~400 LOC) but its extension tax is large: every review-subsystem change must consider guard patterns, receipt-ordering gates, and template parity. fn-101 found the behavioral half of ralph-guard partially inert: receipt-write ordering enforced for Bash only (Write tool bypasses; Stop-hook validation is the real backstop); hooks.json matches `Bash|Execute` but the guard drops tool_name != "Bash" so command checks are silently dead on Droid; `flowctl done` success detected by word-sniffing response prose (ralph-guard.py:733-740). STRATEGY.md already positions pilot+land as the default path.

## Changes

1. **done-detection**: replace the "done/updated/completed" word sniff with a structured signal (tool_response exit code, or require --json and parse it).
2. **Droid mismatch**: Factory hooks reference (re-verified 2026-07-19) still lists `Execute` as canonical for shell (no `Bash`), and Droid file tools are `Edit`/`Create`/`ApplyPatch` (no `Write`) - so BOTH matcher halves are needed for Droid, and the guard body must accept them: tool_name in ("Bash","Execute") at ralph-guard.py:952 and ("Edit","Write","Create","ApplyPatch") at :947, plus `Create|ApplyPatch` added to the hooks.json Edit|Write matcher. Alternative: drop the Droid halves and document Ralph as Claude-Code-only. Pick one; today the files contradict and Droid enforcement is silently inert.
3. **Write-tool receipt bypass**: extend the PreToolUse Edit|Write matcher handling to block receipt-path writes pre-review (parity with the Bash patterns), or explicitly document the Stop-hook as the sole enforcement point and delete the Bash-side ordering theater.
4. **Debug log**: gate the unconditional /tmp append (ralph-guard.py:720-750, 922-955) behind RALPH_GUARD_DEBUG=1; restores the documented zero-overhead claim; use tempfile.gettempdir() (Windows parity, ralph-guard.py:34).
4b. **True no-op for non-Ralph sessions**: the FLOW_RALPH gate lives inside the Python, so any repo that ever ran ralph-init pays a Python spawn per Bash/Edit/Write/Stop event in normal sessions. Add `[ -n "$FLOW_RALPH" ] &&` to the hooks.json command lines (and the bash shim) so non-Ralph sessions never spawn Python.
5. **Dedupe RALPH_ITERATION stamping**: one `stamp_ralph_iteration(receipt)` helper replaces 10 identical blocks (flowctl.py:24396...27280). Coordinate with fn-106.
6. **find_active_runs**: parse progress.txt via the existing `promise=COMPLETE` key=value contract style instead of prose regex, or emit key=value lines from ralph.sh.
7. **Dead weight**: delete RALPH_GUARD_VERSION no-op constant; delete or wire `ralph_e2e_test.sh` (unreferenced) into local-dev.md.
8. **Feature-freeze declaration** (docs, CLAUDE.md + ralph.md): Ralph is maintenance-mode; new pipeline features are not required to thread through guard patterns/ralph templates unless Ralph-relevant. Record the 3.0 revisit (extract to flow-ralph module vs sunset when host-native loop primitives cover the outlast-a-session case).

## Acceptance

- ralph smoke + e2e-short suites green; guard blocks/permits unchanged on Claude Code happy paths.
- Zero /tmp writes when FLOW_RALPH unset (test).
- A Droid decision recorded and the two files consistent.

## Boundaries

- No new guard capabilities. No changes to the fn-55 delegation allowlist (audit verdict: exemplary; leave it alone).
