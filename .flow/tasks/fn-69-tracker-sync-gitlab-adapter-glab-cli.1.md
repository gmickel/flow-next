## Goal
Make `tracker.type: gitlab` a real, activatable tracker: the deterministic flowctl bits (activation enum, config schema, identifier validator) + the discovery-ceremony's coupled sites (probe / ASK / config-write **+ the readiness-label site**), plus Python tests. This wiring makes the GitLab adapter (fn-69.2) reachable end-to-end. (Spec R3, R4-identity, R5-ceremony, R7.)

## Files
- `plugins/flow-next/scripts/flowctl.py` (+ byte-identical `.flow/bin/flowctl.py`):
  - `TRACKER_TYPES` (flowctl.py:1030) — add `"gitlab"` (one-line set membership; the legitimate "validate this enum" flowctl edit). Confirm both use-sites (1522, 21012) inherit via the shared constant.
  - `get_default_config()` — add `tracker.perTracker.project` (group/project path, parallel to GitHub's `repo`) + `tracker.perTracker.host` (self-managed base) schema defaults.
  - `validate_tracker_identifier` (used at cmd_sync_set_tracker_id, flowctl.py:20502) — widen to accept the GitLab `<project>#<iid>` form **including NESTED group paths** (`group/subgroup/project#12`) + bare `#<iid>`: `(?:[^/#]+/)+[^/#]+#\d+` shape, positive iid, no empty segments, preserve display (the fn-64.1-style widening github.md used for `#N` / `owner/repo#N`).
- `plugins/flow-next/skills/flow-next-tracker-sync/steps.md` — the ceremony sites:
  - Probe table (Phase 1, ~steps.md:38) — add a `glab auth status` / `GITLAB_TOKEN`|`CI_JOB_TOKEN` row.
  - ASK step (~steps.md:51) — add a GitLab option to the tracker-choice question (extend the existing linear/github choice, do NOT fork a 4th hardcoded path).
  - Config-write block (~steps.md:55-66) — emit `tracker.type gitlab` + `perTracker.project`/`host` (analogous to the `repo` write).
  - **Readiness-label ceremony site (R5 — the 4th coupled site)** — steps.md currently has only Linear + GitHub readiness branches. Add a GitLab branch: when `tracker.readyState` is a label, **pre-create the label at ceremony time** via the adapter (`glab api`/REST `POST /projects/:id/labels`), **tolerate the already-exists error**, and **never write `tracker.readyState` config on a failed/unconfirmed create** — mirroring the github.md/steps.md pre-create-and-confirm pattern. (The create CALL is documented in fn-69.2's gitlab.md; this task wires the ceremony branch that invokes it.)
- `plugins/flow-next/skills/flow-next-tracker-sync/SKILL.md` — the probe table: add the GitLab signal row + **update the "four signals" count wording to FIVE** everywhere (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/token, Jira host) — prose/counts, not just the row.
- `plugins/flow-next/tests/test_tracker_sync_*.py` — new tests.

## Approach
- Deterministic flowctl only here — enum + config schema + identifier validator. No transport code, no judgment (that is the adapter prose in fn-69.2). Keep `AskUserQuestion` canonical (sync-codex rewrites for the mirror in fn-69.3).
- Mirror the existing GitHub branches in steps.md/SKILL.md verbatim-in-shape (incl. the readiness-label branch); the ceremony stays env > config > ASK, transport resolved once + persisted.

## Acceptance
- `tracker.type: gitlab` flips `sync active` true via the type path (R7).
- `set-tracker-id` accepts `<project>#<iid>` **and nested `group/subgroup/project#12`** + bare `#<iid>`; rejects `group/#12`, `#0` (R4-identity).
- Ceremony offers GitLab and writes `tracker.type gitlab` + `perTracker.project`/`host` on confirmation; surfaces present AND absent (R3).
- **Readiness-label ceremony branch added** — pre-create + tolerate-already-exists + never-write-on-failure (R5).
- Config schema carries the new `perTracker` keys with safe defaults.
- Tests cover: enum activation, config defaults, identifier validation (valid incl. nested + invalid GitLab forms), and a **steps.md presence/grep assertion** (GitLab probe row + ASK option + `tracker.type gitlab`/`perTracker` config-writes + readiness-label branch all present — ceremony is prose, so assert presence, not executable shape). Full suite stays green.

## Test notes
- Python stdlib unittest; mirror existing `test_tracker_sync_*`. No network — test plumbing + validator, never live `glab`.

## Description
TBD

## Done summary
Wired `tracker.type: gitlab` as a real, activatable tracker: added `gitlab` to flowctl's `TRACKER_TYPES` enum (R7), seeded `tracker.perTracker.project`/`host` config defaults (R3), and widened the `set-tracker-id` identifier validator to accept nested GitLab group paths (`group/subgroup/project#12`) + bare `#<iid>` while rejecting empty segments and non-positive iids (R4-identity). Wired the discovery-ceremony prose across both SKILL.md and steps.md (GitLab probe row, ASK option, `tracker.type gitlab` + `perTracker.project`/`host` config-writes, and a pre-create-and-confirm readiness-label branch — R5), updated the probe-count wording four→five, kept `.flow/bin/flowctl.py` byte-identical, and added 22 tests. Plan-review SHIP (rp), full stdlib suite green (1234 tests).
## Evidence
- Commits: 6d45fabdcc0cbd5e489ad71e43fa9cd45eaaed56
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1234 tests OK, skipped=2), python3 -m unittest discover -s plugins/flow-next/tests -p 'test_tracker*.py' (161 OK), python3 -m unittest plugins.flow-next.tests.test_tracker_sync_gitlab (22 OK)
- PRs: