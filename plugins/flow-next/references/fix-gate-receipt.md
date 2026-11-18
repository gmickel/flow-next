# Full-gate receipt after a review fix (gated reference)

> Read from a review fix loop (impl-review fix-loop.md step 5, spec-completion-review
> workflow-common.md step 3) only when the fix's green run included a full-gate command.

When the fix's green run included one of the repo's full-gate commands (the same `(gate_id, exact command string)` identity the worker's Phase 5 maps — e.g. the repo's parallel full-suite entrypoint), nothing changed between that run and this commit, and the tree is clean at the committed fix HEAD: write the receipt — `<FLOWCTL> gate receipt --gate <gate_id> --command="<cmd>"` — so later gates honor it instead of re-running the identical command. Focused/partial test commands NEVER mint a full-gate receipt (identity is the exact full command string). A dirty tree, edits after the run, or any doubt about identity → mint nothing (fail closed; the later gate simply re-runs).
