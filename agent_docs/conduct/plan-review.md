# Conduct checklist — /flow-next:plan-review

A correct run coordinates a Carmack-level review of the current spec through exactly one resolved backend and carries that backend's verdict into the bounded fix loop.

- [ ] The backend is resolved once and only the matching `workflow-<backend>.md` is read; `none`, and a removed `rp` or `export` value (after its removal notice), terminate from the common workflow without loading any backend file.
- [ ] The verdict comes from the backend's receipt or status, never from the coordinator. A transcript where the session declares SHIP on its own reading of the spec has broken this.
- [ ] A backend or transport failure ends with `RETRY: no verdict (backend or transport failure)` and stops (a `CLI message:` reporting a usage, credit or spend limit is reported in its place), with no fallback to a different backend. Re-framing a delivered `NEEDS_WORK` as a transport problem to reclaim a round has broken this.
- [ ] `NEEDS_WORK` fixes follow the working rules' Review section: findings showing the spec is wrong are fixed and written to the current user-edited spec via `flowctl spec set-plan`, affected task specs are synced, the rest are listed as follow-ups, and the re-review re-enters the same backend. The loop never asks the user; round counting stays flowctl-owned, and `MAJOR_RETHINK` stops with `BLOCKED: DESIGN_CONFLICT`.
- [ ] Each `flowctl <backend> plan-review` call runs as one blocking foreground call with a generous timeout, never backgrounded and polled.
- [ ] When the verdict's `maintainability:` block names a finding under either key, one `Maintainability (plan review): duplication - ...; structure - ...` line is appended to the spec's `## Decision Context` via `flowctl spec set-plan` in the round the finding arrived, whatever the verdict. A block reading `none identified` under both keys, or no block, writes nothing.
