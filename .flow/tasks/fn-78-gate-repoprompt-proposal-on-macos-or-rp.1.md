# fn-78-gate-repoprompt-proposal-on-macos-or-rp.1 Gate the RepoPrompt proposal in /flow-next:plan & plan-review (macOS-or-rp-cli eligibility)

## Description

Add a single `RP_ELIGIBLE` eligibility gate to the two canonical skills so the RepoPrompt (context-scout / rp) path is only *proposed* when it can actually run — on macOS, or when `rp-cli` is on PATH. Inline bash probe mirroring setup's `HAVE_RP` idiom (`flow-next-setup/workflow.md:325`) plus a `uname` arm. Interactive proposal surfaces only; no changes to flowctl backend resolution or `require_rp_cli`. Canonical Claude-native files only — the Codex mirror regen is task .2.

## Acceptance

- **R1:** A single eligibility predicate `RP_ELIGIBLE = (uname == "Darwin") OR (command -v rp-cli succeeds)` is computed at the start of the interactive-setup step in **both** canonical `flow-next-plan/SKILL.md` and `flow-next-plan-review/SKILL.md`, POSIX-portable (`uname`, `command -v`), mirroring setup's `HAVE_RP` idiom plus a `uname` arm.
- **R2:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Research question does NOT offer the RepoPrompt / context-scout option in either branch (`SKILL.md:122-123` already-configured, `SKILL.md:140-141` unconfigured); research defaults to `repo-scout` without asking about RepoPrompt.
- **R3:** In `/flow-next:plan`, when `RP_ELIGIBLE=0`, the Review question (`SKILL.md:144-148`) does NOT list "RepoPrompt" (`:146`); remaining choices render as a clean, correctly-lettered list.
- **R4:** In `/flow-next:plan-review`, when `RP_ELIGIBLE=0`, the backend guidance the user is *steered toward* — the Backends summary line (`SKILL.md:14`), the "Backend at a glance" list (`~:61`), and the ASK-error recommendation — drops `rp` and presents only the runnable **configured** review backends `codex`, `copilot`, `cursor` (plus `none`). `export` is an explicit one-off review MODE (`--review=export`), NOT a configured `review.backend`, so it is never presented as a configured backend. The `--review=rp` flag stays *accepted* (R6); only the proactive steering drops rp. On `RP_ELIGIBLE=1` the full set (rp included) renders unchanged.
- **R5:** When `RP_ELIGIBLE=1` (macOS, or rp-cli present), ALL proposal surfaces render exactly as today — byte-for-byte (rp present, same wording/order).
- **R6:** Proposal-suppression is not a ban: an explicit `--research=rp` (plan) or `--review=rp` / `FLOW_REVIEW_BACKEND=rp` / `review.backend=rp` (plan-review) is still honored and reaches the runtime `require_rp_cli()` path (`flowctl.py:1593`) — identical to today.
- **R9 (a, b — this task's slice):** Verification is explicit: on `RP_ELIGIBLE=0`, inspect the canonical plan + plan-review SKILL text and confirm the rp research/review option and rp backend-steering are absent with the remaining options a clean correctly-lettered list (no dangling "b)"); on `RP_ELIGIBLE=1`, confirm the eligible rendering is byte-for-byte the pre-change wording (rp present).

**Files:** `plugins/flow-next/skills/flow-next-plan/SKILL.md`, `plugins/flow-next/skills/flow-next-plan-review/SKILL.md` (canonical only — do NOT hand-edit the codex mirror; that is task .2). Inline bash probe only — no new flowctl surface; do not touch flowctl backend resolution / `require_rp_cli`. `steps.md:160` already degrades dispatch on rp-unavailable; this gates the earlier *proposal*.

## Done summary
Added the RP_ELIGIBLE gate (uname Darwin OR rp-cli on PATH) to canonical flow-next-plan and flow-next-plan-review SKILL.md: on ineligible hosts the RepoPrompt research/review proposals and rp backend steering (Backends summary, at-a-glance, ASK-error, override hints) are suppressed with clean re-lettering, while eligible rendering stays byte-for-byte and explicit --research=rp/--review=rp remain honored via runtime require_rp_cli. Codex mirror regen is task .2.
## Evidence
- Commits: a7c20fb7, 9298b9e9d931574eba407d003d1d52d21c67355f
- Tests: bash -n + live execution of RP_ELIGIBLE guard (Darwin=1; simulated Linux w/o rp-cli=0), cursor impl-review fn-78.1 --base 7354f9bb: NEEDS_WORK then SHIP (all R-IDs met)
- PRs: