# Conduct checklist — /flow-next:plan-review

A correct run coordinates a Carmack-level review of the current spec through exactly one resolved backend and carries that backend's verdict into the bounded fix loop.

- [ ] The backend is resolved once and only the matching `workflow-<backend>.md` is read; `none` and `export` terminate from the common workflow without loading any backend file.
- [ ] The verdict comes from the backend's receipt or status, never from the coordinator. A transcript where the session declares SHIP on its own reading of the spec has broken this.
- [ ] A backend or transport failure ends with `<promise>RETRY</promise>` and stops, with no fallback to a different backend. Re-framing a delivered `NEEDS_WORK` as a transport problem to reclaim a round has broken this.
- [ ] `NEEDS_WORK` fixes are written to the current user-edited spec via `flowctl spec set-plan`, affected task specs are synced, and the re-review re-enters the same backend.
- [ ] Round counting stays flowctl-owned — no agent-side counter — and `MAJOR_RETHINK` stops with the typed design-conflict escalation rather than entering the fix loop.
- [ ] Each `flowctl <backend> plan-review` call runs as one blocking foreground call with a generous timeout, never backgrounded and polled.
