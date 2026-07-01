# fn-78-gate-repoprompt-proposal-on-macos-or-rp.1 Gate the RepoPrompt proposal in /flow-next:plan & plan-review (macOS-or-rp-cli eligibility)

## Description
TBD

## Acceptance
## Acceptance Criteria (fn-78 R1–R6)

- **R1:** A single eligibility predicate `RP_ELIGIBLE = (uname == "Darwin") OR (command -v rp-cli succeeds)` is computed at the start of the interactive-setup step in **both** canonical `flow-next-plan/SKILL.md` and `flow-next-plan-review/SKILL.md`, POSIX-portable (`uname`, `command -v`), mirroring setup's existing `HAVE_RP` idiom (`flow-next-setup/workflow.md:325`) plus a `uname` arm.
- **R2:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Research question does NOT offer the RepoPrompt / context-scout option in either branch (`SKILL.md:122-123` already-configured, `SKILL.md:140-141` unconfigured); research defaults to `repo-scout` without asking about RepoPrompt.
- **R3:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Review question (`SKILL.md:144-148`) does NOT list "RepoPrompt" (`:146`); remaining choices render as a clean, correctly-lettered list.
- **R4:** In `/flow-next:plan-review`, when `RP_ELIGIBLE=0`, the backend guidance the user sees (Backends line `SKILL.md:14`, the `--review=rp|…` priority/override hints, the "at a glance" steering) omits `rp` and lists only runnable backends (`codex|copilot|cursor|export|none`).
- **R5:** When `RP_ELIGIBLE=1` (macOS, or rp-cli present), ALL proposal surfaces render exactly as today — no wording/order/option change (byte-for-byte for the eligible path).
- **R6:** Proposal-suppression is not a ban: an explicit `--research=rp` (plan) or `--review=rp` / `FLOW_REVIEW_BACKEND=rp` / `review.backend=rp` (plan-review) is still honored and reaches the existing runtime `require_rp_cli()` path (`flowctl.py:1593`) — behavior identical to today.

**Files:** `plugins/flow-next/skills/flow-next-plan/SKILL.md`, `plugins/flow-next/skills/flow-next-plan-review/SKILL.md` (canonical, Claude-native — do NOT hand-edit the codex mirror; that is task .2).

**Notes:** inline bash probe only — no new flowctl surface. steps.md:160 already degrades dispatch on rp-unavailable; this gates the earlier *proposal*. Scope is the interactive proposal surfaces only; do not touch flowctl backend resolution or `require_rp_cli`.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
