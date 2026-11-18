# Full-gate receipts (gated reference)

> Read from phases.md Phase 4 only when a full gate (test) command is about to run there.

- For each full gate (test) command that would run, first probe `$FLOWCTL gate check --gate <gate_id> --command="<cmd>"`; exit 0 means skip that re-run and note `Gates: baseline reused (green receipt <sha8>)` for the Phase 5 final summary. On nonzero, run it. After any passing full gate run here, write its receipt with `$FLOWCTL gate receipt --gate <gate_id> --command="<cmd>"`.
