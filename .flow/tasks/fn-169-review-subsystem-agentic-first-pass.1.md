---
satisfies: [R1]
---
# fn-169-review-subsystem-agentic-first-pass.1 Resume dispatch parity: sandbox, effort, git-check — and loud failure

## Description
Give the resume path the same guarantees as a fresh dispatch, and stop it failing silently. Independently shippable — this closes a live read-only-contract violation and is the spec's early proof point.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`run_codex_exec` resume branch ~:4353; the copilot/cursor exec paths), `plugins/flow-next/tests/` (new resume-parity tests), `.flow/bin/flowctl.py` (propagation)

### Approach
- The resume argv is `cmd = [codex, "exec", "resume", session_id, "-"]` — no `--sandbox`, no `-c model_reasoning_effort`, no `--skip-git-repo-check`. Measured consequences on this machine: a resumed review reports `sandbox: danger-full-access` (inherited from ambient `~/.codex/config.toml`) and `reasoning effort: medium` instead of the configured value.
- Pass all three, mirroring the fresh `_dispatch` branch (~:4398). The resumed session's MODEL is fixed by the original dispatch and must NOT be re-pinned (PR #203 r2 already handles that via `resolution_out["resumed"]`) — only sandbox, effort and the repo-check flag are being restored.
- **Make failure loud.** Today `except subprocess.CalledProcessError: pass` falls through to a fresh session with `resolution_out["resumed"]` unset, exit 0, normal-looking output — so a blind re-review is indistinguishable from a resumed one. Set an explicit signal (e.g. `resolution_out["resume_failed"]` + the reason) and log to stderr. Do not change the fallback BEHAVIOUR in this task — unconditional injection still covers it; `.3` is what makes the signal load-bearing.
- Audit the copilot (`--session-id` / `--resume`, marker-tracked) and cursor (`--resume`, resume-only, `require_nonempty_sid`) paths for the same three defect classes and fix what applies. Cursor takes no effort flag by design.
- **Verify the unverified cases while you are here** (spec Open Questions): does resume survive (a) separate flowctl processes, and (b) a gap of minutes rather than seconds? Record the answers in the done summary — `.3` depends on them.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py` ~:4340-4420 — the resume branch and the fresh `_dispatch` it must match
- `run_copilot_exec` / `run_cursor_exec` — the sibling resume paths
- `BACKEND_REGISTRY` resume_modes: codex ~:40364, copilot ~:40384, cursor ~:40404

**Optional:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md` — the read-only reviewer contract this restores

### Key context
- **The three defects are ALREADY MEASURED** (spec § Already established): `danger-full-access`, `medium`, and the silent non-git fallthrough. Do NOT re-probe them to confirm — go straight to the fix and pin each with a regression test. The only NEW measurement in this task is resume across separate processes and after a multi-minute gap.
- The reviewer read-only contract is stated in the impl-review skill: "never widen the reviewer sandbox: reviewers are read-only by contract, so a sandbox-blocked reviewer means something asked it to mutate the workspace." Resumed reviews have been violating it.
- Every round 2+ review in the fn-168 workstream ran under `danger-full-access`. This is live, not theoretical.
- Do NOT make injection conditional here — that is `.3`, and it must not land before resume is trustworthy.

## Acceptance
- [ ] Resume passes `--sandbox`, the configured reasoning effort, and `--skip-git-repo-check`; a test asserts the resumed CLI header reports the intended sandbox and effort (regression target: `danger-full-access` / `medium`)
- [ ] The resumed session's model is still NOT re-pinned (the `resumed` resolution contract is preserved)
- [ ] Resume failure is SURFACED: an explicit signal plus a stderr line; a test forces failure (non-git cwd) and asserts the signal is set rather than a silent fresh session
- [ ] Fallback behaviour unchanged in this task — injection is still unconditional
- [ ] copilot and cursor resume paths audited for the same three defect classes; fixes applied where they apply, with the audit result stated in the done summary
- [ ] Resume verified across separate flowctl processes AND after a multi-minute gap; both results recorded in the done summary
- [ ] Focused suites green; propagation done (cp flowctl.py to .flow/bin)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
