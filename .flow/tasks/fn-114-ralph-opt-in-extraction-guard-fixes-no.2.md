# fn-114-ralph-opt-in-extraction-guard-fixes-no.2 Ralph surface extraction to ralphctl.py + status soft-probe

## Description
Extract the ralph surface out of flowctl core into the ralph-init scaffold.

**Size:** M
**Files:** both flowctl.py copies, plugins/flow-next/skills/flow-next-ralph-init/templates/ (new ralphctl.py or ralph.sh helpers), tests

### Approach

- Read spec section B. Move flowctl ralph pause/resume/stop/status (~90 LOC sentinel plumbing) and find_active_runs progress.txt parsing (~90 LOC) into a repo-local scripts/ralph/ralphctl.py installed by ralph-init (template lives under the ralph-init skill; ralph.sh callers updated).
- flowctl status: SOFT-PROBE (PLAN DECISION in spec) - the active-runs section renders only when scripts/ralph/runs/ exists, via a tolerant read (no import of ralphctl; just the dir/progress files). Zero cost otherwise.
- RALPH_ITERATION stamping: already deduped into stamp_ralph_iteration by fn-112 - verify, do not re-extract (note in summary).
- sync-codex.sh: confirm the codex mirror never shipped hooks and remove any hooks.json handling if present.
- Non-blocking: grep flow-next-tui for flowctl ralph status / active-runs JSON consumers; if the move breaks the TUI, NOTE it in the summary (maintainer: follow-up spec, not a blocker).
- Re-pin tests exercising flowctl ralph subcommands (they move or die with the extraction; the template's ralphctl.py gets its own focused test if the repo pattern supports template tests).
- Dual-copy; sync-codex x2. NO git commands, no em dashes.

### Acceptance

- [ ] flowctl has no ralph pause/resume/stop/status; ralphctl.py template ships them; ralph.sh updated
- [ ] flowctl status soft-probes (present-dir renders, absent-dir zero cost, no crash either way)
- [ ] TUI consumer check reported; focused suites green; dual-copy identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
