# Work-loop gate diet: green receipts + docs-only gate tiering + event-driven waits

## Goal & Context

The fn-89 pipeline run was trace-mined end to end (2026-07-19 post-mortem, memory `session-2026-07-19-fn89-shipped`): of 2h41 work-tick-to-PR, actual implementation was ~425s (4.4%) while ~50% went to the full unittest suite executing 10 times in one work stage. Every worker runs the suite twice (pre-baseline + post-gate), each pre-baseline re-proves green on exactly the commit the previous worker's post-gate just certified, and the host re-ran it an 11th-hour fourth time on the same tree. Worst case: the docs-only task (.3) spent 84% of its 55 minutes on suite x4 + smoke x2 - gates its diff could not break - while the REVIEW layer correctly triage-skipped the same diff in 2 seconds.

The fix is mechanical, not semantic: (a) remember, keyed by commit hash, that a tree state was already proven green; (b) classify a diff by file path as unable to affect the executable surface. Both are pure plumbing - exactly the flowctl carve-out. The spec deliberately does NOT touch the fn-83 territory: "did this change semantically affect that plan?" remains a judgment question and its deterministic-skip ban stands. "Is this byte-identical tree already proven green?" and "does this diff touch only non-executable prose?" are not judgment questions.

## Requirements

- R1 **Green receipt (baseline reuse).** When a worker's post-gate suite passes, write a receipt `{head_sha, gate_id (e.g. unittest|smoke), timestamp}` to a gitignored ledger (`.flow/tmp/green-receipts.json` or similar, flowctl-owned atomic write). A later pre-baseline gate in the SAME repo state (HEAD == receipt sha AND clean non-.flow worktree) honors the receipt and skips the re-run. Fail-closed: dirty tree, sha mismatch, missing receipt, or unparseable ledger -> run the full gate as today.
- R2 **Docs-only gate tiering.** Deterministic diff classification of the task's change set (git diff --name-only vs the task base): when EVERY path matches the non-executable class (`*.md` outside skill-executable dirs? NO - define precisely: docs/, agent_docs/, CHANGELOG.md, README*, .flow/**, *.mdx; NOT scripts/, NOT tests/, NOT skill/agent .md files that sync-codex validates - those keep the sync-codex idempotency+guard gate) run a tier-B gate set (sync-codex x2 + guards when mirror-relevant paths changed; targeted greps; nothing else) instead of full unittest + smoke. ANY path outside the class -> full gates. The class list is a committed whitelist in flowctl (mirroring the existing deterministic review triage-skip whitelist - same philosophy, gate layer).
- R3 **Skipped gates are loud.** Every honored receipt / tier-B classification is recorded in the task's done evidence tests[] (`"unittest: SKIPPED via green receipt <sha8>"` / `"full gates: SKIPPED via docs-only classification"`) and echoed in the worker summary. Never a silent skip.
- R4 **Event-driven waits.** Worker/skill prose replaces fixed `sleep 25`/`sleep 60` poll loops for background jobs (codex exec, background suite runs) with short-interval until-loops or completion-signal waits; bound every loop.
- R5 **Scope guard.** No semantic skipping anywhere: the fn-83 do-not-re-attempt decision record binds for judgment questions. Everything in this spec keys ONLY on commit hashes, worktree cleanliness, and file-path whitelists.
- R6 **Measurement.** After landing, re-run the trace post-mortem method on the next comparable pilot run; acceptance target: total gate time <=50% of the fn-89 baseline share with zero green->red regressions attributable to a skipped gate.
- R7 **Cross-platform.** The receipt ledger + classification live in flowctl (host-agnostic); worker.md prose changes walk the CLAUDE.md cross-platform checklist (sync-codex mirror regen + guards; Cursor/Droid get canonical prose as-is - no Claude-only constructs).

## Key files / interfaces

- `plugins/flow-next/skills/flow-next-work/references/worker.md` (pre-baseline + post-gate steps)
- `plugins/flow-next/skills/flow-next-work/phases.md` (host Phase 4/5 quality re-run)
- `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl` dual-copy (receipt ledger subcommands, e.g. `flowctl gate receipt` / `flowctl gate check`; diff classifier `flowctl gate classify`)
- `scripts/sync-codex.sh` (mirror + guards for worker.md prose changes)
- `plugins/flow-next/tests/` (ledger atomicity, fail-closed paths, classifier whitelist)

## Decision Context

- Post-mortem evidence: fn-89 run, suite x10 = ~4,800s of 9,640s; docs-only task 84% gate time. Implementation was 4.4%.
- Deliberate contrast with fn-83 (killed plan-sync shadow gate): that was a deterministic proxy for a semantic question and produced a false skip. This spec's predicates are hash equality and path membership - no semantics. The burden-of-proof framing from fn-101 applies: these belong IN flowctl because no judgment is involved.
- Review triage-skip precedent: the review layer already classifies docs-only diffs deterministically and skips in 2s (receipt `mode: triage_skip`); this spec extends the same trust boundary to the gate layer.
